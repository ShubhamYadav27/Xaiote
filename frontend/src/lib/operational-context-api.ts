import { fetchApi } from './api';

export interface OperationalContext {
  work_order_id: string;
  status: string;
  product_id?: string;
  planned_quantity?: number;
  actual_quantity?: number;
  machine_id?: string;
  [key: string]: any;
}

export async function getOperationalContextForWorkOrder(woId: string): Promise<OperationalContext> {
  return fetchApi(`/operational-context/work-orders/${woId}`);
}
