import asyncio, uuid, os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from app.models.company import Company
from app.models.plant import Plant
from app.models.masters import Machine, Product, Customer
from app.models.work_order import WorkOrder

async def m():
    e = create_async_engine('postgresql+asyncpg://user:password@db:5432/xaiote')
    async with AsyncSession(e) as s:
        res = await s.execute(text('SELECT id FROM companies LIMIT 1'))
        comp_id = res.scalar()
        if not comp_id:
            c = Company(id=str(uuid.uuid4()), name='Test Co')
            s.add(c)
            await s.flush()
            comp_id = c.id
        
        res = await s.execute(text('SELECT id FROM plants LIMIT 1'))
        plant_id = res.scalar()
        if not plant_id:
            p = Plant(id=str(uuid.uuid4()), company_id=comp_id, name='Main Plant', timezone='UTC')
            s.add(p)
            await s.flush()
            plant_id = p.id
            
        prod = Product(id=str(uuid.uuid4()), company_id=comp_id, sku='PROD-1', name='Product 1')
        cust = Customer(id=str(uuid.uuid4()), company_id=comp_id, name='Customer 1')
        s.add_all([prod, cust])
        await s.flush()
        
        m = Machine(id=str(uuid.uuid4()), company_id=comp_id, plant_id=plant_id, name='CNC 2')
        s.add(m)
        await s.flush()
        
        wo = WorkOrder(id=str(uuid.uuid4()), company_id=comp_id, plant_id=plant_id, machine_id=m.id, product_id=prod.id, customer_id=cust.id, order_number='WO-1234', quantity=100, status='IN_PROGRESS')
        s.add(wo)
        await s.commit()
        print('Inserted CNC 2 and WO-1234')
asyncio.run(m())
