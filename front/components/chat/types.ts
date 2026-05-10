export type ChartType = "bar" | "line" | "pie" | "area" | "composed" | "table" | "horizontal_bar" | "kpi" | "scatter"

export interface ChartConfig {
  should_render: boolean
  type: ChartType
  title: string
  description: string
  x_key: string
  y_keys: string[]
  data: Record<string, unknown>[]
  warnings?: string[]
}

export interface AgentFilters {
  intent: string
  tables_used: string[]
  row_count: number
  truncated: boolean
  cross_check_performed: boolean
  execution_time_ms: number
}

export interface AgentResponse {
  answer: string
  intent: string
  sql: string
  validation_sql: string
  filters: AgentFilters
  chart: ChartConfig
  status: "success" | "error" | "partial" | "ambiguous"
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  text: string
  question?: string
  chart?: ChartConfig | null
  sql?: string
  intent?: string
  status?: string
  executionMs?: number
  feedback?: "up" | "down"
  timestamp: Date
}
