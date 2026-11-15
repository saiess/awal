export interface Narrator {
  id: string;
  label: string;
  language: string;
  reference_audio_relative_path: string;
  reference_sha256: string;
}

export interface Segment {
  id: string;
  order: number;
  text: string;
  status: 'pending' | 'generating' | 'ready' | 'failed';
  stale: boolean;
  audio_path: string | null;
  version: number;
  duration_seconds: number | null;
  error: string | null;
}

export interface ExportSettings {
  speed: number;
  processed: boolean;
  enhance: boolean;
  gap_seconds: number;
}

export interface ExportOptions extends ExportSettings {
  format: 'wav' | 'mp3';
  include_segments: boolean;
  segment_ids: string[] | null;
}

export interface ExportRecord {
  id: string;
  duration_seconds: number;
  effective_speed: number;
  options: ExportOptions;
  sha256: string;
}

export interface Project {
  id: string;
  title: string;
  script: string;
  narrator_id: string;
  narrator: Narrator;
  export_settings: ExportSettings;
  exports: ExportRecord[];
  segments: Segment[];
}

export interface ProjectSummary {
  id: string;
  title: string;
  ready_count: number;
  segment_count: number;
}

export interface Job {
  id: string;
  project_id: string;
  status: 'queued' | 'generating' | 'ready' | 'failed' | 'interrupted';
  total_segments: number;
  done_segments: number;
  active_segment_id: string | null;
  error: string | null;
}

export interface Health {
  gpu_available: boolean;
  engine_loaded: boolean;
  busy: boolean;
  active_job: Job | null;
}
