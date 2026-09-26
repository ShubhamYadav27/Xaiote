from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.infrastructure.database.session import AsyncSessionLocal
from app.models.communication import ExtractedEventCandidate
from app.models.manufacturing_event import (
    EventStatus,
    ManufacturingEvent,
    TemporalProvenance,
)
from app.workers.canonicalization_worker import process_one_job
from app.workers.resolution_worker import process_one_candidate
from tests.test_phase_3f_validation import setup_base_data


@pytest.mark.asyncio
async def test_temporal_explicit_timestamp():
    async with AsyncSessionLocal() as db_session:
        comp, p1, p2, m1, wo1, cand = await setup_base_data(db_session)
        cand.payload = {
            **cand.payload,
            "event_time_reference": "2026-09-24T10:00:00+00:00",
        }
        db_session.add(cand)
        await db_session.commit()
        cand_id = cand.id

    while await process_one_candidate("worker-1"):
        pass
    async with AsyncSessionLocal() as db_session:
        cand_db = await db_session.get(ExtractedEventCandidate, cand_id)
        print(f"cand processing status: {cand_db.processing_status}")
        from app.models.resolution import EntityResolutionResult

        er = (
            (
                await db_session.execute(
                    select(EntityResolutionResult).where(
                        EntityResolutionResult.candidate_id == cand_id
                    )
                )
            )
            .scalars()
            .first()
        )
        if er:
            print(f"ER status: {er.overall_status}")

    while await process_one_job("worker-canonical-1"):
        pass

    async with AsyncSessionLocal() as db_session:
        ev = (
            (
                await db_session.execute(
                    select(ManufacturingEvent).where(
                        ManufacturingEvent.candidate_id == cand_id
                    )
                )
            )
            .scalars()
            .first()
        )
        assert ev is not None
        assert ev.event_time_reference == "2026-09-24T10:00:00+00:00"
        assert ev.temporal_provenance == TemporalProvenance.EXPLICIT_TIMESTAMP
        assert ev.canonical_occurrence_timestamp == datetime(
            2026, 9, 24, 10, 0, tzinfo=timezone.utc
        )


@pytest.mark.asyncio
async def test_temporal_ambiguous_relative():
    async with AsyncSessionLocal() as db_session:
        comp, p1, p2, m1, wo1, cand = await setup_base_data(db_session)
        cand.payload = {**cand.payload, "event_time_reference": "kal"}
        db_session.add(cand)
        await db_session.commit()
        cand_id = cand.id

    while await process_one_candidate("worker-1"):
        pass
    async with AsyncSessionLocal() as db_session:
        cand_db = await db_session.get(ExtractedEventCandidate, cand_id)
        print(f"cand processing status: {cand_db.processing_status}")
        from app.models.resolution import EntityResolutionResult

        er = (
            (
                await db_session.execute(
                    select(EntityResolutionResult).where(
                        EntityResolutionResult.candidate_id == cand_id
                    )
                )
            )
            .scalars()
            .first()
        )
        if er:
            print(f"ER status: {er.overall_status}")

    while await process_one_job("worker-canonical-1"):
        pass

    async with AsyncSessionLocal() as db_session:
        ev = (
            (
                await db_session.execute(
                    select(ManufacturingEvent).where(
                        ManufacturingEvent.candidate_id == cand_id
                    )
                )
            )
            .scalars()
            .first()
        )
        assert ev is not None
        assert ev.event_time_reference == "kal"
        assert ev.temporal_provenance == TemporalProvenance.UNKNOWN
        assert ev.canonical_occurrence_timestamp is None


@pytest.mark.asyncio
async def test_temporal_missing_reference():
    async with AsyncSessionLocal() as db_session:
        comp, p1, p2, m1, wo1, cand = await setup_base_data(db_session)
        cand.payload = {
            k: v for k, v in cand.payload.items() if k != "event_time_reference"
        }
        db_session.add(cand)
        await db_session.commit()
        cand_id = cand.id

    while await process_one_candidate("worker-1"):
        pass
    async with AsyncSessionLocal() as db_session:
        cand_db = await db_session.get(ExtractedEventCandidate, cand_id)
        print(f"cand processing status: {cand_db.processing_status}")
        from app.models.resolution import EntityResolutionResult

        er = (
            (
                await db_session.execute(
                    select(EntityResolutionResult).where(
                        EntityResolutionResult.candidate_id == cand_id
                    )
                )
            )
            .scalars()
            .first()
        )
        if er:
            print(f"ER status: {er.overall_status}")

    while await process_one_job("worker-canonical-1"):
        pass

    async with AsyncSessionLocal() as db_session:
        ev = (
            (
                await db_session.execute(
                    select(ManufacturingEvent).where(
                        ManufacturingEvent.candidate_id == cand_id
                    )
                )
            )
            .scalars()
            .first()
        )
        assert ev is not None
        assert ev.event_time_reference is None
        assert ev.temporal_provenance == TemporalProvenance.UNKNOWN
        assert ev.canonical_occurrence_timestamp is None


@pytest.mark.asyncio
async def test_temporal_invalid_reference():
    async with AsyncSessionLocal() as db_session:
        comp, p1, p2, m1, wo1, cand = await setup_base_data(db_session)
        cand.payload = {
            **cand.payload,
            "event_time_reference": "this is obviously not a date",
        }
        db_session.add(cand)
        await db_session.commit()
        cand_id = cand.id

    while await process_one_candidate("worker-1"):
        pass
    async with AsyncSessionLocal() as db_session:
        cand_db = await db_session.get(ExtractedEventCandidate, cand_id)
        print(f"cand processing status: {cand_db.processing_status}")
        from app.models.resolution import EntityResolutionResult

        er = (
            (
                await db_session.execute(
                    select(EntityResolutionResult).where(
                        EntityResolutionResult.candidate_id == cand_id
                    )
                )
            )
            .scalars()
            .first()
        )
        if er:
            print(f"ER status: {er.overall_status}")

    while await process_one_job("worker-canonical-1"):
        pass

    async with AsyncSessionLocal() as db_session:
        ev = (
            (
                await db_session.execute(
                    select(ManufacturingEvent).where(
                        ManufacturingEvent.candidate_id == cand_id
                    )
                )
            )
            .scalars()
            .first()
        )
        assert ev is not None
        assert ev.event_time_reference == "this is obviously not a date"
        assert ev.temporal_provenance == TemporalProvenance.UNKNOWN
        assert ev.canonical_occurrence_timestamp is None


@pytest.mark.asyncio
async def test_temporal_deterministic_relative_fallback():
    async with AsyncSessionLocal() as db_session:
        comp, p1, p2, m1, wo1, cand = await setup_base_data(db_session)
        cand.payload = {**cand.payload, "event_time_reference": "yesterday"}
        db_session.add(cand)
        await db_session.commit()
        cand_id = cand.id

    while await process_one_candidate("worker-1"):
        pass
    async with AsyncSessionLocal() as db_session:
        cand_db = await db_session.get(ExtractedEventCandidate, cand_id)
        print(f"cand processing status: {cand_db.processing_status}")
        from app.models.resolution import EntityResolutionResult

        er = (
            (
                await db_session.execute(
                    select(EntityResolutionResult).where(
                        EntityResolutionResult.candidate_id == cand_id
                    )
                )
            )
            .scalars()
            .first()
        )
        if er:
            print(f"ER status: {er.overall_status}")

    while await process_one_job("worker-canonical-1"):
        pass

    async with AsyncSessionLocal() as db_session:
        ev = (
            (
                await db_session.execute(
                    select(ManufacturingEvent).where(
                        ManufacturingEvent.candidate_id == cand_id
                    )
                )
            )
            .scalars()
            .first()
        )
        assert ev is not None
        assert ev.event_time_reference == "yesterday"
        assert ev.temporal_provenance == TemporalProvenance.UNKNOWN
        assert ev.canonical_occurrence_timestamp is None

        ev.temporal_provenance = TemporalProvenance.HUMAN_CONFIRMED
        ev.canonical_occurrence_timestamp = datetime(
            2026, 9, 23, 12, 0, tzinfo=timezone.utc
        )
        db_session.add(ev)
        await db_session.commit()

        ev2 = await db_session.get(ManufacturingEvent, ev.id)
        assert ev2.temporal_provenance == TemporalProvenance.HUMAN_CONFIRMED

        ev2.temporal_provenance = TemporalProvenance.DETERMINISTIC_RELATIVE_REFERENCE
        db_session.add(ev2)
        await db_session.commit()

        ev3 = await db_session.get(ManufacturingEvent, ev.id)
        assert (
            ev3.temporal_provenance
            == TemporalProvenance.DETERMINISTIC_RELATIVE_REFERENCE
        )


@pytest.mark.asyncio
async def test_regression_canonicalization_behavior():
    async with AsyncSessionLocal() as db_session:
        comp, p1, p2, m1, wo1, cand = await setup_base_data(db_session)
        cand.payload = {**cand.payload, "event_time_reference": "2026-09-24T10:00:00Z"}
        db_session.add(cand)
        await db_session.commit()
        cand_id = cand.id

    while await process_one_candidate("worker-1"):
        pass
    async with AsyncSessionLocal() as db_session:
        cand_db = await db_session.get(ExtractedEventCandidate, cand_id)
        print(f"cand processing status: {cand_db.processing_status}")
        from app.models.resolution import EntityResolutionResult

        er = (
            (
                await db_session.execute(
                    select(EntityResolutionResult).where(
                        EntityResolutionResult.candidate_id == cand_id
                    )
                )
            )
            .scalars()
            .first()
        )
        if er:
            print(f"ER status: {er.overall_status}")

    while await process_one_job("worker-canonical-1"):
        pass

    async with AsyncSessionLocal() as db_session:
        ev = (
            (
                await db_session.execute(
                    select(ManufacturingEvent).where(
                        ManufacturingEvent.candidate_id == cand_id
                    )
                )
            )
            .scalars()
            .first()
        )
        assert ev is not None
        assert ev.event_status == EventStatus.CANONICAL
