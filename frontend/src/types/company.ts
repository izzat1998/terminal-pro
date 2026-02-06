export interface Company {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  telegram_group_id: string | null;
  telegram_group_name: string;
  notifications_enabled: boolean;
  billing_method: 'split' | 'exit_month';
  legal_address: string;
  inn: string;
  mfo: string;
  bank_account: string;
  bank_name: string;
  contract_number: string;
  contract_date: string | null;
  contract_expires: string | null;
  contract_file: string | null;
  customers_count: number;
  entries_count: number;
  balance_usd: string;
  balance_uzs: string;
  draft_invoices_count: number;
  created_at: string;
  updated_at: string;
}
