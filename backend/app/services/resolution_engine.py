import datetime
import logging
import re
import string

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.masters import Customer, Machine, Product, Vendor
from app.models.work_order import WorkOrder

logger = logging.getLogger(__name__)


def normalize_string(text_val: str, entity_type: str) -> str:
    if not text_val:
        return ""

    # Common: lowercase and strip outer/internal whitespace
    s = text_val.lower().strip()
    s = re.sub(r"\s+", " ", s)

    if entity_type in ["machine", "work_order"]:
        # Retain hyphens/underscores, strip trailing punctuation
        # We can just remove trailing punctuation
        # string.punctuation in python is: !"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~
        # We need to retain hyphens and underscores
        remove_chars = string.punctuation.replace("-", "").replace("_", "")
        # Create a regex to match trailing chars from remove_chars
        # re.escape escapes all of them
        pattern = f"[{re.escape(remove_chars)}]+$"
        s = re.sub(pattern, "", s)
    elif entity_type in ["customer", "vendor", "product"]:
        # retain ALL punctuation, so do nothing more
        pass

    return s


class ResolutionEngine:
    def __init__(self, db: AsyncSession, company_id: str):
        self.db = db
        self.company_id = company_id

        self.thresholds = {
            "machine": (0.85, 0.15),
            "work_order": (0.90, 0.10),
            "customer": (0.85, 0.10),
            "vendor": (0.85, 0.10),
            "product": (0.85, 0.10),
        }

    async def _fetch_candidates(self, model, field, plant_id: str | None = None):
        stmt = select(
            model.id, field, model.plant_id if hasattr(model, "plant_id") else None
        ).where(model.company_id == self.company_id)
        if plant_id and hasattr(model, "plant_id"):
            stmt = stmt.where(model.plant_id == plant_id)
        result = await self.db.execute(stmt)
        return result.all()  # [(id, name, plant_id), ...]

    async def _resolve_entity(
        self, entity_type: str, raw_text: str, model, field, plant_id: str | None = None
    ) -> tuple[str, str | None, str | None]:
        # returns (status, resolved_id, resolved_plant_id)
        # plant_id is the context. If provided, we filter by it (if applicable).

        # 1. RAW EXACT
        stmt = select(model.id)
        if hasattr(model, "plant_id"):
            stmt = stmt.add_columns(model.plant_id)
        stmt = stmt.where(model.company_id == self.company_id, field == raw_text)
        if plant_id and hasattr(model, "plant_id"):
            stmt = stmt.where(model.plant_id == plant_id)

        result = await self.db.execute(stmt)
        matches = result.all()
        if len(matches) == 1:
            return (
                "RESOLVED",
                matches[0][0],
                matches[0][1] if len(matches[0]) > 1 else None,
            )
        elif len(matches) > 1:
            return "AMBIGUOUS", None, None

        # 2. NORMALIZED EXACT
        normalized_input = normalize_string(raw_text, entity_type)
        # We have to fetch all and check, or do we use db level?
        # Let's do it in python memory if it's not too big, or use SQL.
        # But SQL normalization is tricky without writing a custom function. We can just use python since we don't have a huge DB for the tests.
        candidates = await self._fetch_candidates(model, field, plant_id)

        normalized_matches = []
        for cand in candidates:
            cand_id = cand[0]
            cand_raw = cand[1]
            cand_plant_id = cand[2] if len(cand) > 2 else None
            cand_norm = normalize_string(cand_raw, entity_type)
            if cand_norm == normalized_input:
                normalized_matches.append((cand_id, cand_plant_id))

        if len(normalized_matches) == 1:
            return "RESOLVED", normalized_matches[0][0], normalized_matches[0][1]
        elif len(normalized_matches) > 1:
            return "AMBIGUOUS", None, None

        # 3. FUZZY MATCH
        # Use pg_trgm similarity
        threshold, margin = self.thresholds[entity_type]

        # We need to query using pg_trgm similarity between raw_text and field.
        # Actually, maybe normalized fuzzy or raw fuzzy? The spec says:
        # "RAW_EXACT -> NORMALIZED_EXACT -> FUZZY -> UNRESOLVED/AMBIGUOUS"
        # We will use raw_text for fuzzy with func.similarity

        stmt = select(model.id, field, func.similarity(field, raw_text).label("sim"))
        if hasattr(model, "plant_id"):
            stmt = stmt.add_columns(model.plant_id)

        stmt = stmt.where(model.company_id == self.company_id)
        stmt = stmt.where(func.similarity(field, raw_text) >= threshold)
        if plant_id and hasattr(model, "plant_id"):
            stmt = stmt.where(model.plant_id == plant_id)

        stmt = stmt.order_by(func.similarity(field, raw_text).desc())

        result = await self.db.execute(stmt)
        fuzzy_matches = result.all()  # [(id, name, sim, plant_id), ...]

        if not fuzzy_matches:
            return "UNRESOLVED", None, None

        top_sim = fuzzy_matches[0].sim

        # Find how many are within the margin
        close_matches = [m for m in fuzzy_matches if top_sim - m.sim <= margin]

        if len(close_matches) == 1:
            return (
                "RESOLVED",
                close_matches[0][0],
                close_matches[0][3] if len(close_matches[0]) > 3 else None,
            )
        else:
            return "AMBIGUOUS", None, None

    async def process(self, payload: dict) -> dict:
        # payload is the extracted event schema dictionary
        # Returns a dict of state and ids

        result_state = {
            "work_order_state": "REFERENCE_ABSENT",
            "work_order_id": None,
            "machine_state": "REFERENCE_ABSENT",
            "machine_id": None,
            "customer_state": "REFERENCE_ABSENT",
            "customer_id": None,
            "vendor_state": "REFERENCE_ABSENT",
            "vendor_id": None,
            "product_state": "REFERENCE_ABSENT",
            "product_id": None,
        }

        wo_ref = payload.get("work_order_reference")
        wo_val = wo_ref.get("value") if wo_ref else None
        wo_plant_id = None

        if wo_val and wo_val.strip():
            state, w_id, p_id = await self._resolve_entity(
                "work_order", wo_val, WorkOrder, WorkOrder.order_number
            )
            result_state["work_order_state"] = state
            result_state["work_order_id"] = w_id
            wo_plant_id = p_id

        mach_ref = payload.get("machine_reference")
        mach_val = mach_ref.get("value") if mach_ref else None
        if mach_val and mach_val.strip():
            # We use wo_plant_id if available.
            # "if a WO exactly matches, use its plant_id for Machine resolution. Otherwise, if no plant context, and there are plant collisions -> AMBIGUOUS."
            # Wait, the WO might not exactly match, it might fuzzy match. The instruction says "if a WO exactly matches". But wait, if it's RESOLVED (even by fuzzy), does it count as plant context? Let's use wo_plant_id if WO is RESOLVED.
            state, m_id, _ = await self._resolve_entity(
                "machine", mach_val, Machine, Machine.name, plant_id=wo_plant_id
            )
            result_state["machine_state"] = state
            result_state["machine_id"] = m_id

        cust_ref = payload.get("customer_reference")
        cust_val = cust_ref.get("value") if cust_ref else None
        if cust_val and cust_val.strip():
            state, c_id, _ = await self._resolve_entity(
                "customer", cust_val, Customer, Customer.name
            )
            result_state["customer_state"] = state
            result_state["customer_id"] = c_id

        vend_ref = payload.get("vendor_reference")
        vend_val = vend_ref.get("value") if vend_ref else None
        if vend_val and vend_val.strip():
            state, v_id, _ = await self._resolve_entity(
                "vendor", vend_val, Vendor, Vendor.name
            )
            result_state["vendor_state"] = state
            result_state["vendor_id"] = v_id

        prod_ref = payload.get("product_reference")
        prod_val = prod_ref.get("value") if prod_ref else None
        if prod_val and prod_val.strip():
            state, p_id, _ = await self._resolve_entity(
                "product", prod_val, Product, Product.name
            )
            result_state["product_state"] = state
            result_state["product_id"] = p_id

        return result_state

    async def submit_human_review(
        self,
        result_id: str,
        entity_type: str,
        canonical_id: str,
        user_id: str,
    ) -> dict:
        if not user_id:
            raise ValueError("Authentication required: user_id missing")

        valid_entity_types = ["machine", "work_order", "customer", "vendor", "product"]
        if entity_type not in valid_entity_types:
            raise ValueError(f"Invalid entity type: {entity_type}")

        from app.models.resolution import EntityResolutionResult

        stmt = select(EntityResolutionResult).where(
            EntityResolutionResult.id == result_id,
            EntityResolutionResult.company_id == self.company_id,
        )
        res = await self.db.execute(stmt)
        er = res.scalars().first()
        if not er:
            raise ValueError("Result not found or tenant mismatch")

        model_map = {
            "machine": Machine,
            "work_order": WorkOrder,
            "customer": Customer,
            "vendor": Vendor,
            "product": Product,
        }
        import typing

        model: typing.Any = model_map[entity_type]
        c_stmt = select(model).where(
            model.id == canonical_id, model.company_id == self.company_id
        )
        c_res = await self.db.execute(c_stmt)
        canonical = c_res.scalars().first()
        if not canonical:
            raise ValueError("Canonical entity not found or tenant mismatch")

        if entity_type == "machine" and er.work_order_id:
            wo_stmt = select(WorkOrder.plant_id).where(WorkOrder.id == er.work_order_id)
            wo_res = await self.db.execute(wo_stmt)
            wo_plant = wo_res.scalars().first()
            if (
                hasattr(canonical, "plant_id")
                and wo_plant
                and canonical.plant_id != wo_plant
            ):
                raise ValueError("Plant mismatch with context work order")

        audit_entry = {
            "user_id": user_id,
            "entity_type": entity_type,
            "canonical_id": canonical_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        current_audit: list = er.human_review_audit or []
        new_audit = list(current_audit)
        new_audit.append(audit_entry)
        er.human_review_audit = new_audit

        setattr(er, f"{entity_type}_state", "RESOLVED")
        setattr(er, f"{entity_type}_id", canonical_id)

        states = [
            er.machine_state,
            er.work_order_state,
            er.customer_state,
            er.vendor_state,
            er.product_state,
        ]
        if all(s in ["RESOLVED", "REFERENCE_ABSENT"] for s in states):
            er.overall_status = "COMPLETED"
            er.processing_status = "COMPLETED"
            from app.models.manufacturing_event import CanonicalizationJob

            # check if one already exists
            j_stmt = select(CanonicalizationJob).where(
                CanonicalizationJob.candidate_id == er.candidate_id
            )
            j_res = await self.db.execute(j_stmt)
            if not j_res.scalars().first():
                job = CanonicalizationJob(candidate_id=er.candidate_id)
                self.db.add(job)

        return {"status": "success", "overall_status": er.overall_status}
