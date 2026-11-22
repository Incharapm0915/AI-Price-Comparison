import { apiClient } from "./apiClient";
import type { AlertOut, CreateAlertRequest } from "@/types/alert";

export async function createAlert(payload: CreateAlertRequest): Promise<AlertOut> {
  const { data } = await apiClient.post<AlertOut>("/alerts", payload);
  return data;
}

export async function listAlerts(email: string): Promise<AlertOut[]> {
  const { data } = await apiClient.get<AlertOut[]>("/alerts", { params: { email } });
  return data;
}

export async function deleteAlert(alertId: string): Promise<void> {
  await apiClient.delete(`/alerts/${alertId}`);
}
