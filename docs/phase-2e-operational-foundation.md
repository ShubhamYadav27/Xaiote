# Phase 2E: Operational Data Foundation & Usability Hardening

## Overview
This document outlines the changes made to harden the operational Next.js UI using the existing real backend APIs. The frontend now serves as a robust operational data foundation.

## Features Implemented
1. **API Client Integration:**
   - Centralized `fetchApi` utility for standard backend interactions.
   - Proper tenant isolation handling via `access_token` injection into the `Authorization` header.

2. **Entity List & Form Pages:**
   - Customers
   - Vendors
   - Products
   - Machines
   - Work Orders
   - All pages feature pagination, loading states, error handling, and create modals.

3. **Import Flow UI:**
   - Unified upload page for importing Customers, Vendors, Products, and Machines from CSV.
   - Import Job detail page containing validation status and a paginated data table for `ImportAudit` rows.

4. **Security & Data Safety:**
   - No mock data or fake AI workflows.
   - Strict adherence to the backend envelope format (`{ data: ... }`, `{ error: ... }`).

## Usage
Start the development server using `docker compose up`. The dashboard is accessible via `http://localhost:3000`.