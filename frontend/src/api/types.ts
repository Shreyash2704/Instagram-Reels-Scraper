export type SourceType = "hashtag" | "profile" | "post_url" | "profile_tagged";

export type RunStatus = "pending" | "running" | "completed" | "failed";

export interface SourceRead {
  id: number;
  type: SourceType;
  value: string;
  created_at?: string | null;
}

export interface SourceReadList {
  items: SourceRead[];
}

export interface RunReadList {
  items: RunRead[];
}

export interface RunRead {
  id: number;
  source_id: number;
  status: RunStatus;
  error_message: string | null;
  item_count: number;
  video_count: number;
  delivered_count: number;
  destination_status_code: number | null;
  apify_dataset_id: string | null;
  payload_preview: string | null;
  created_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface RunCreateResponse {
  run_id: number;
  status: RunStatus;
}

/** Normalized video item from pipeline payload_preview JSON */
export interface VideoPayloadItem {
  source_type?: string;
  source_value?: string;
  instagram_shortcode?: string | null;
  permalink?: string | null;
  video_url?: string | null;
  cdn_video_url?: string | null;
  thumbnail_url?: string | null;
  caption?: string | null;
  taken_at?: string | null;
  author_username?: string | null;
  is_video?: boolean;
}
