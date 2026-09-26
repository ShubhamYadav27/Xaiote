import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_imports_comprehensive():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        run_id = str(uuid.uuid4())
        # Setup Company A
        await ac.post(
            "/api/auth/register",
            json={
                "email": f"a_{run_id}@masters.com",
                "password": "p",
                "full_name": "A",
                "company_name": "CA",
            },
        )
        token_a = (
            await ac.post(
                "/api/auth/login",
                json={"email": f"a_{run_id}@masters.com", "password": "p"},
            )
        ).json()["data"]["access_token"]
        auth_a = {"Authorization": f"Bearer {token_a}"}

        # Setup Company B
        await ac.post(
            "/api/auth/register",
            json={
                "email": f"b_{run_id}@masters.com",
                "password": "p",
                "full_name": "B",
                "company_name": "CB",
            },
        )
        token_b = (
            await ac.post(
                "/api/auth/login",
                json={"email": f"b_{run_id}@masters.com", "password": "p"},
            )
        ).json()["data"]["access_token"]
        auth_b = {"Authorization": f"Bearer {token_b}"}

        # --- 1. Basic Upload & Idempotency & Provenance ---
        csv_1 = b"name,external_id\nCust 1,EXT1\nCust 2,EXT2\n"
        files_1 = {"file": ("c1.csv", csv_1, "text/csv")}
        res_1 = await ac.post(
            "/api/v1/imports/upload",
            headers=auth_a,
            data={"import_type": "CUSTOMERS"},
            files=files_1,
        )
        assert res_1.status_code == 200
        job_1_id = res_1.json()["data"]["id"]

        # Verify job
        job_1 = (await ac.get(f"/api/v1/imports/{job_1_id}", headers=auth_a)).json()[
            "data"
        ]
        assert job_1["status"] == "COMPLETED"
        assert job_1["valid_rows"] == 2

        # Same file hash rejection
        files_1_dup = {"file": ("c1.csv", csv_1, "text/csv")}
        res_dup = await ac.post(
            "/api/v1/imports/upload",
            headers=auth_a,
            data={"import_type": "CUSTOMERS"},
            files=files_1_dup,
        )
        assert res_dup.status_code == 400

        # --- 2. Record update via different file & Duplicate rows in same CSV ---
        csv_2 = (
            b"name,external_id\nCust 1 Updated,EXT1\nCust 1 Updated,EXT1\nCust 3,EXT3\n"
        )
        files_2 = {"file": ("c2.csv", csv_2, "text/csv")}
        res_2 = await ac.post(
            "/api/v1/imports/upload",
            headers=auth_a,
            data={"import_type": "CUSTOMERS"},
            files=files_2,
        )
        assert res_2.status_code == 200

        custs_a = (await ac.get("/api/v1/customers", headers=auth_a)).json()["data"][
            "items"
        ]
        names = {c["external_id"]: c["name"] for c in custs_a}
        assert names["EXT1"] == "Cust 1 Updated"
        assert len(names) == 3

        # --- 3. Invalid rows entering Audit, not canonical ---
        csv_err = b"name,external_id\n,EXT4\nCust 5,EXT5\n"
        files_err = {"file": ("cerr.csv", csv_err, "text/csv")}
        res_err = await ac.post(
            "/api/v1/imports/upload",
            headers=auth_a,
            data={"import_type": "CUSTOMERS"},
            files=files_err,
        )
        job_err_id = res_err.json()["data"]["id"]

        job_err = (
            await ac.get(f"/api/v1/imports/{job_err_id}", headers=auth_a)
        ).json()["data"]
        assert job_err["status"] == "COMPLETED_WITH_ERRORS"

        audits = (
            await ac.get(f"/api/v1/imports/{job_err_id}/audits", headers=auth_a)
        ).json()["data"]["items"]
        assert audits[0]["validation_status"] == "INVALID"

        custs_err_check = (await ac.get("/api/v1/customers", headers=auth_a)).json()[
            "data"
        ]["items"]
        assert "EXT4" not in [c["external_id"] for c in custs_err_check]

        # --- 4. Tenant Isolation ---
        res_b_job = await ac.get(f"/api/v1/imports/{job_1_id}", headers=auth_b)
        assert res_b_job.status_code == 404

        res_b_audits = await ac.get(
            f"/api/v1/imports/{job_1_id}/audits", headers=auth_b
        )
        assert res_b_audits.status_code == 404

        # --- 5. File Limits Rejection (> 25MB) ---
        large_csv = b"a" * (25 * 1024 * 1024 + 10)
        files_large = {"file": ("large.csv", large_csv, "text/csv")}
        res_large = await ac.post(
            "/api/v1/imports/upload",
            headers=auth_a,
            data={"import_type": "CUSTOMERS"},
            files=files_large,
        )
        assert res_large.status_code == 400

        # --- 6. Row Limits (> 50,000) ---
        huge_rows_csv = b"name,external_id\n" + b"A,B\n" * 50001
        files_huge = {"file": ("huge.csv", huge_rows_csv, "text/csv")}
        res_huge = await ac.post(
            "/api/v1/imports/upload",
            headers=auth_a,
            data={"import_type": "CUSTOMERS"},
            files=files_huge,
        )
        assert res_huge.status_code == 200
        job_huge_id = res_huge.json()["data"]["id"]
        job_huge = (
            await ac.get(f"/api/v1/imports/{job_huge_id}", headers=auth_a)
        ).json()["data"]
        assert job_huge["status"] == "FAILED"
        assert "50,000" in job_huge["error_message"]

        # --- 7. Unknown references in Work Order ---
        csv_wo = b"order_number,plant_id,product_id,quantity\nWO1,plant999,prod999,10\n"
        files_wo = {"file": ("wo.csv", csv_wo, "text/csv")}
        res_wo = await ac.post(
            "/api/v1/imports/upload",
            headers=auth_a,
            data={"import_type": "WORK_ORDERS"},
            files=files_wo,
        )
        job_wo_id = res_wo.json()["data"]["id"]

        job_wo = (await ac.get(f"/api/v1/imports/{job_wo_id}", headers=auth_a)).json()[
            "data"
        ]
        assert job_wo["status"] == "COMPLETED_WITH_ERRORS"

        audits_wo = (
            await ac.get(f"/api/v1/imports/{job_wo_id}/audits", headers=auth_a)
        ).json()["data"]["items"]
        assert audits_wo[0]["validation_status"] == "INVALID"
        assert "Plant reference is unknown" in audits_wo[0]["validation_reason"]
