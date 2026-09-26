import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_provenance_and_data_quality():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        run_id = str(uuid.uuid4())
        # Setup Company A
        await ac.post(
            "/api/auth/register",
            json={
                "email": f"p_{run_id}@masters.com",
                "password": "p",
                "full_name": "P",
                "company_name": "CP",
            },
        )
        token = (
            await ac.post(
                "/api/auth/login",
                json={"email": f"p_{run_id}@masters.com", "password": "p"},
            )
        ).json()["data"]["access_token"]
        auth = {"Authorization": f"Bearer {token}"}

        # 1. Create first import
        csv_1 = b"name,external_id\nCust 1,EXT1\nCust 2,EXT2\n"
        res_1 = await ac.post(
            "/api/v1/imports/upload",
            headers=auth,
            data={"import_type": "CUSTOMERS"},
            files={"file": ("c1.csv", csv_1, "text/csv")},
        )
        assert res_1.status_code == 200
        job_1_id = res_1.json()["data"]["id"]

        job_1 = (await ac.get(f"/api/v1/imports/{job_1_id}", headers=auth)).json()[
            "data"
        ]
        assert job_1["status"] == "COMPLETED"
        assert job_1["created_rows"] == 2
        assert job_1["updated_rows"] == 0
        assert job_1["unchanged_rows"] == 0

        # Verify master has source_import_job_id
        custs = (await ac.get("/api/v1/customers", headers=auth)).json()["data"][
            "items"
        ]
        assert len(custs) == 2
        for c in custs:
            assert c["source_import_job_id"] == job_1_id

        # Verify audit actions
        audits_1 = (
            await ac.get(f"/api/v1/imports/{job_1_id}/audits", headers=auth)
        ).json()["data"]["items"]
        assert len(audits_1) == 2
        for a in audits_1:
            assert a["action"] == "CREATED"
            assert a["previous_source_import_job_id"] is None
            assert a["target_record_id"] is not None

        # 2. Second import: 1 update, 1 unchanged, 1 new
        csv_2 = b"name,external_id\nCust 1 Updated,EXT1\nCust 2,EXT2\nCust 3,EXT3\n"
        res_2 = await ac.post(
            "/api/v1/imports/upload",
            headers=auth,
            data={"import_type": "CUSTOMERS"},
            files={"file": ("c2.csv", csv_2, "text/csv")},
        )
        job_2_id = res_2.json()["data"]["id"]

        job_2 = (await ac.get(f"/api/v1/imports/{job_2_id}", headers=auth)).json()[
            "data"
        ]
        assert job_2["status"] == "COMPLETED"
        assert job_2["created_rows"] == 1
        assert job_2["updated_rows"] == 1
        assert job_2["unchanged_rows"] == 1

        audits_2 = (
            await ac.get(f"/api/v1/imports/{job_2_id}/audits", headers=auth)
        ).json()["data"]["items"]
        actions = {a["action"]: a for a in audits_2}
        assert "CREATED" in actions
        assert "UPDATED" in actions
        assert "UNCHANGED" in actions

        assert actions["UPDATED"]["previous_source_import_job_id"] == job_1_id
        assert actions["UNCHANGED"]["previous_source_import_job_id"] == job_1_id

        # 3. Work Order with quantity = 0 -> NEEDS_REVIEW
        # Need plant and product first
        plant_res = await ac.post(
            "/api/v1/plants",
            headers=auth,
            json={"name": "Plant 1", "location": "L1", "timezone": "UTC"},
        )
        assert plant_res.status_code == 200, plant_res.json()
        plant_id = plant_res.json()["data"]["id"]
        prod_res = await ac.post(
            "/api/v1/products", headers=auth, json={"name": "Prod 1"}
        )
        prod_id = prod_res.json()["data"]["id"]

        csv_wo = f"order_number,plant_id,product_id,quantity\nWO1,{plant_id},{prod_id},0\nWO2,{plant_id},{prod_id},10\n".encode()
        res_wo = await ac.post(
            "/api/v1/imports/upload",
            headers=auth,
            data={"import_type": "WORK_ORDERS"},
            files={"file": ("wo.csv", csv_wo, "text/csv")},
        )
        job_wo_id = res_wo.json()["data"]["id"]

        job_wo = (await ac.get(f"/api/v1/imports/{job_wo_id}", headers=auth)).json()[
            "data"
        ]
        assert job_wo["needs_review_rows"] == 1
        assert (
            job_wo["valid_rows"] == 2
        )  # still valid technically, just needs review. Wait, valid_count only increments if success. Yes, success=True, needs_review=True.

        audits_wo = (
            await ac.get(f"/api/v1/imports/{job_wo_id}/audits", headers=auth)
        ).json()["data"]["items"]
        status_counts = [a["validation_status"] for a in audits_wo]
        assert "NEEDS_REVIEW" in status_counts
        assert "VALID" in status_counts
