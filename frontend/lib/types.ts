export type Role = "HOSPITAL" | "DISTRICT_ADMIN" | "STATE_ADMIN" | "CENTRAL_ADMIN";

export type User = {
  user_id: string;
  username: string;
  name: string;
  role: Role;
  hospital_id?: string | null;
  state?: string | null;
  district?: string | null;
};

export type ReferralStatus =
  | "PENDING"
  | "ACCEPTED"
  | "REJECTED"
  | "IN_TRANSIT"
  | "ARRIVED"
  | "TREATMENT_ACTIVE"
  | "IN_TREATMENT"
  | "COMPLETED"
  | "TRANSFERRED"
  | "DIED"
  | "CLOSED";

export type Priority = "Critical" | "Urgent" | "Stable";

export type BedType = "ICU" | "GENERAL" | "EMERGENCY" | "VENTILATOR";

export type Referral = {
  referral_id: string;
  patient_id: string;
  from_hospital_id: string;
  to_hospital_id: string;
  from_hospital_name?: string;
  to_hospital_name?: string;
  from_district?: string;
  to_district?: string;
  from_state?: string;
  to_state?: string;
  reason: string;
  priority: Priority | string;
  status: ReferralStatus;
  bed_type?: BedType | string;
  bed_id?: string;
  bed_number?: string;
  reservation_status?: string;
  auto_reservation?: boolean;
  reservation_message?: string;
  reservation_release_status?: string;
  ambulance_id?: string | null;
  eta_minutes?: number | null;
  notes?: string | null;
  rejection_reason?: string | null;
  created_at: string;
  accepted_at?: string | null;
  rejected_at?: string | null;
  dispatched_at?: string | null;
  in_transit_at?: string | null;
  arrived_at?: string | null;
  treatment_started_at?: string | null;
  completed_at?: string | null;
  transferred_at?: string | null;
  died_at?: string | null;
  closed_at?: string | null;
};

export type BedCategoryStats = {
  total: number;
  available: number;
  reserved: number;
  occupied: number;
  maintenance?: number;
};

export type BedInventory = {
  hospital_id: string;
  hospital_name?: string;
  name?: string;
  state?: string;
  district?: string;
  city?: string;
  total_beds?: number;
  total_general_beds?: number;
  available_beds: number;
  total_icu_beds?: number;
  available_icu_beds: number;
  reserved_beds: number;
  reserved_icu_beds: number;
  occupied_beds?: number;
  occupied_icu_beds?: number;
  total_emergency_beds?: number;
  available_emergency_beds?: number;
  reserved_emergency_beds?: number;
  occupied_emergency_beds?: number;
  total_available_beds?: number;
  total_reserved_beds?: number;
  total_occupied_beds?: number;
  total_capacity?: number;
  oxygen_support?: string;
  ventilator?: string;
  ambulance?: string;
  blood_bank?: string;
  emergency_24x7?: string;
  is_configured?: boolean;
  categories?: {
    GENERAL?: BedCategoryStats;
    ICU?: BedCategoryStats;
    EMERGENCY?: BedCategoryStats;
  };
};

export type HospitalRecommendation = {
  hospital_id: string;
  hospital_name: string;
  name?: string;
  state?: string;
  district?: string;
  city?: string;
  distance_km?: number | null;
  eta_minutes?: number;
  available_beds: number;
  available_icu_beds: number;
  ventilators?: string;
  ambulance?: string;
  specialties?: string[];
  final_score?: number;
  match_score?: number;
  success_probability?: number | null;
  specialty_match?: number;
  bed_match?: number;
  icu_match?: number;
  test_match?: number;
  recommendation_type?: string;
  reasons?: string[];
  ai_rationale?: string[];
  disqualification_reasons?: string[];
  is_eligible?: boolean;
  rank?: number;
};

export type NotificationItem = {
  notification_id: string;
  id?: number | string;
  referral_id?: string;
  hospital_id?: string;
  application_id?: string;
  action_url?: string;
  event_type: string;
  title: string;
  message: string;
  priority: string;
  is_read: boolean;
  created_at: string;
};

export type Patient = {
  visit_id?: number | string;
  patient_id: string;
  name: string;
  age: number;
  gender: string;
  disease: string;
  priority: Priority | string;
  icu_required: string;
  status: string;
  admission_type?: string;
  admitted_at?: string;
  treatment_started_at?: string;
  completed_at?: string;
  blood_group?: string;
  contact_phone?: string;
  emergency_contact?: string;
  address?: string;
  district?: string;
  state?: string;
  chief_complaint?: string;
  severity_level?: string;
  bed_type?: string;
  required_specialty?: string;
  vitals?: {
    heart_rate?: number;
    systolic_bp?: number;
    diastolic_bp?: number;
    blood_pressure?: string;
    spo2?: number;
    temperature?: number;
    respiratory_rate?: number;
    gcs_score?: number;
  };
  clinical_notes?: string;
  referral_status?: string;
  active_referral?: {
    referral_id?: string;
    status?: string;
    to_hospital_id?: string;
    created_at?: string;
  };
};

export interface PatientIntakePayload {
  name: string;
  age: number;
  gender: string;
  blood_group?: string;
  contact_phone?: string;
  emergency_contact?: string;
  address?: string;
  district?: string;
  state?: string;
  chief_complaint: string;
  required_specialty?: string;
  bed_type_assigned?: string;
  severity_level?: string;
  vitals?: {
    heart_rate?: number;
    systolic_bp?: number;
    diastolic_bp?: number;
    blood_pressure?: string;
    spo2?: number;
    temperature?: number;
    respiratory_rate?: number;
    gcs_score?: number;
  };
  clinical_notes?: string;
  patient_id?: string;
}

export interface ConditionAssessmentPayload {
  condition_summary: string;
  urgency: "ROUTINE" | "URGENT" | "EMERGENCY" | "CRITICAL" | string;
  required_specialty?: string;
  required_bed_type?: "GENERAL" | "ICU" | "VENTILATOR" | "EMERGENCY" | "NICU" | string;
  transport_requirement?: "NONE" | "BASIC_AMBULANCE" | "ALS_AMBULANCE" | string;
  vitals?: {
    heart_rate?: number;
    systolic_bp?: number;
    diastolic_bp?: number;
    blood_pressure?: string;
    spo2?: number;
    temperature?: number;
    respiratory_rate?: number;
    gcs_score?: number;
  };
}

export type DistrictMetrics = {
  total_hospitals: number;
  total_beds: number;
  available_beds: number;
  occupied_beds: number;
  bed_occupancy_rate: number;
  total_icu_beds: number;
  available_icu_beds: number;
  occupied_icu_beds: number;
  icu_occupancy_rate: number;
  total_active_referrals: number;
  pending_referrals: number;
  in_transit_referrals: number;
  approved_hospitals?: number;
  approved_applications?: number;
  pending_applications?: number;
  rejected_applications?: number;
  total_reserved_beds?: number;
  total_referrals?: number;
};

export type CriticalAlert = {
  severity: "CRITICAL" | "WARNING" | "INFO";
  type: string;
  hospital_id?: string;
  hospital_name?: string;
  message: string;
};

export type DistrictHospital = {
  hospital_id: string;
  name: string;
  state: string;
  district: string;
  city: string;
  total_beds: number;
  available_beds: number;
  icu_beds: number;
  available_icu_beds: number;
  emergency_24x7: boolean;
  cardiology: boolean;
  neurology: boolean;
  ventilator: boolean;
  ambulance: boolean;
  ct_scan: boolean;
};

export type StateMetrics = {
  total_districts: number;
  total_hospitals: number;
  total_beds: number;
  available_beds: number;
  bed_occupancy_rate: number;
  total_icu_beds: number;
  available_icu_beds: number;
  icu_occupancy_rate: number;
  total_referrals: number;
  approved_hospitals?: number;
  approved_applications?: number;
  pending_applications?: number;
  rejected_applications?: number;
  total_reserved_beds?: number;
};

export type DistrictSummary = {
  district: string;
  hospitals: number;
  total_beds: number;
  available_beds: number;
  total_icu: number;
  available_icu: number;
  occupancy_rate: number;
};

export type CentralMetrics = {
  participating_states: number;
  total_hospitals: number;
  total_beds: number;
  available_beds: number;
  bed_occupancy_rate: number;
  total_icu_beds: number;
  available_icu_beds: number;
  icu_occupancy_rate: number;
  total_referrals: number;
  interstate_referrals: number;
  approved_hospitals?: number;
  approved_applications?: number;
  pending_applications?: number;
  rejected_applications?: number;
  total_reserved_beds?: number;
};

export type StateSummary = {
  state: string;
  hospitals: number;
  total_beds: number;
  available_beds: number;
  total_icu: number;
  available_icu: number;
  occupancy_rate: number;
};

// ============================================================
// REGISTRATION & VERIFICATION SYSTEM TYPES (Phase 1 & Phase 2)
// ============================================================

export type ApplicantType = "STATE" | "DISTRICT" | "HOSPITAL";

export type ApplicationStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "UNDER_REVIEW"
  | "CORRECTION_REQUIRED"
  | "APPROVED"
  | "REJECTED"
  | "PROVISIONED";

export type ApplicationStage =
  | "DISTRICT_REVIEW"
  | "STATE_REVIEW"
  | "CENTRAL_REVIEW"
  | "FINAL_APPROVAL"
  | "PROVISIONING";

export type DocumentType =
  | "CLINICAL_LICENSE"
  | "FIRE_SAFETY_NOC"
  | "POLLUTION_CONTROL_NOC"
  | "MEDICAL_COUNCIL_AFFILIATION"
  | "GOVERNMENT_ORDER"
  | "IDENTITY_PROOF"
  | "OTHER";

export type VerificationStatus = "PENDING" | "VERIFIED" | "REJECTED";

export interface DocumentMetadata {
  document_id: string;
  application_id: string;
  document_type: DocumentType | string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  verification_status: VerificationStatus | string;
  reviewer_remarks?: string | null;
  uploaded_at: string;
}

export interface Milestone {
  stage: string;
  action: string;
  status: string;
  timestamp?: string | null;
}

export interface ApplicantApplication {
  application_id: string;
  application_number: string;
  applicant_type: ApplicantType | string;
  applicant_name: string;
  applicant_email: string;
  applicant_phone: string;
  state: string;
  district?: string | null;
  city?: string | null;
  address?: string | null;
  pincode?: string | null;
  official_designation?: string | null;
  nodal_officer_name?: string | null;
  status: ApplicationStatus | string;
  current_stage: ApplicationStage | string;
  resubmission_version: number;
  created_at: string;
  submitted_at?: string | null;
  resubmitted_at?: string | null;
  rejection_reason?: string | null;
  correction_notes?: string | null;
  profile_data?: Record<string, unknown> | null;
  documents: DocumentMetadata[];
  milestones: Milestone[];
}

export interface PublicTrackingData {
  application_number: string;
  applicant_type: ApplicantType | string;
  applicant_name: string;
  state: string;
  district?: string | null;
  status: ApplicationStatus | string;
  current_stage: ApplicationStage | string;
  created_at?: string | null;
  submitted_at?: string | null;
  resubmission_version: number;
  milestones: Milestone[];
}

export interface OTPRequestPayload {
  contact_target: string;
  channel?: "EMAIL" | "SMS";
  purpose?: "REGISTRATION_OTP" | "LOGIN_OTP" | "PASSWORD_RESET_OTP" | "PORTAL_ACCESS_OTP";
  application_number?: string;
}

export interface OTPRequestResponse {
  token_id: string;
  contact_target: string;
  channel: string;
  resend_available_in_seconds: number;
  expires_in_seconds: number;
  message: string;
}

export interface OTPVerifyPayload {
  token_id: string;
  otp: string;
  purpose?: "REGISTRATION_OTP" | "LOGIN_OTP" | "PASSWORD_RESET_OTP" | "PORTAL_ACCESS_OTP";
  application_number?: string;
}

export interface OTPVerifyResponse {
  verified: boolean;
  contact_target: string;
  application_number?: string | null;
  applicant_token?: string | null;
  token_type?: string | null;
  message: string;
}

export interface CreateStateApplicationPayload {
  applicant_name: string;
  applicant_email: string;
  applicant_phone: string;
  state: string;
  official_designation?: string;
  nodal_officer_name?: string;
  address?: string;
  pincode?: string;
  profile_data?: Record<string, unknown>;
}

export interface CreateDistrictApplicationPayload {
  applicant_name: string;
  applicant_email: string;
  applicant_phone: string;
  state: string;
  district: string;
  official_designation?: string;
  nodal_officer_name?: string;
  address?: string;
  pincode?: string;
  profile_data?: Record<string, unknown>;
}

export interface CreateHospitalApplicationPayload {
  applicant_name: string;
  applicant_email: string;
  applicant_phone: string;
  state: string;
  district: string;
  city?: string;
  address?: string;
  pincode?: string;
  official_designation?: string;
  nodal_officer_name?: string;
  profile_data?: Record<string, unknown>;
}

export interface ApplicationCreationResponse {
  application_id: string;
  application_number: string;
  applicant_type: string;
  applicant_name: string;
  state: string;
  district?: string | null;
  status: string;
  current_stage: string;
  tracking_token: string;
  applicant_token: string;
  created_at: string;
  message: string;
}

export interface SubmitApplicationResponse {
  application_id: string;
  application_number: string;
  status: string;
  current_stage: string;
  submitted_at: string;
  tracking_token: string;
  message: string;
}

export interface ResubmitApplicationResponse {
  application_id: string;
  application_number: string;
  status: string;
  current_stage: string;
  resubmission_version: number;
  resubmitted_at: string;
  message: string;
}

// ============================================================
// PHASE 2D: REVIEWER WORKFLOW & DOSSIER TYPES
// ============================================================

export interface ReviewerApplicationSummary {
  application_id: string;
  application_number: string;
  applicant_type: string;
  applicant_name: string;
  applicant_email: string;
  applicant_phone: string;
  state: string;
  district?: string | null;
  status: string;
  current_stage: string;
  resubmission_version: number;
  created_at: string;
  submitted_at?: string | null;
  documents_count: number;
  pending_documents_count: number;
}

export interface ReviewerApplicationListResponse {
  total: number;
  applications: ReviewerApplicationSummary[];
}

export interface ReviewerDocumentItem {
  document_id: string;
  document_type: string;
  original_filename: string;
  file_size_bytes: number;
  checksum_sha256?: string;
  verification_status: VerificationStatus | string;
  reviewer_remarks?: string | null;
  uploaded_at: string;
}

export interface ReviewerAuditHistoryItem {
  action: string;
  review_tier: string;
  previous_status: string;
  new_status: string;
  reviewer_user_id: string;
  remarks?: string | null;
  created_at?: string | null;
}

export interface ReviewerApplicationDetail {
  application_id: string;
  application_number: string;
  applicant_type: string;
  applicant_name: string;
  applicant_email: string;
  applicant_phone: string;
  state: string;
  district?: string | null;
  city?: string | null;
  address?: string | null;
  pincode?: string | null;
  official_designation?: string | null;
  nodal_officer_name?: string | null;
  status: ApplicationStatus | string;
  current_stage: ApplicationStage | string;
  resubmission_version: number;
  profile_data?: Record<string, unknown> | null;
  correction_notes?: string | null;
  rejection_reason?: string | null;
  created_at: string;
  submitted_at?: string | null;
  documents: ReviewerDocumentItem[];
  history: ReviewerAuditHistoryItem[];
}

export interface VerifyDocumentPayload {
  verification_status: "VERIFIED" | "REJECTED";
  reviewer_remarks?: string;
}

export interface ReviewDecisionPayload {
  action: "FORWARD" | "APPROVE" | "REJECT";
  remarks?: string;
}

export interface ReviewDecisionResponse {
  application_id: string;
  application_number: string;
  action: string;
  new_status: string;
  new_stage: string;
  message: string;
  provisioning_user_id?: string | null;
  provisioning_username?: string | null;
}

export interface RequestCorrectionPayload {
  correction_notes: string;
}

// ============================================================
// PHASE 2D: ACCOUNT ACTIVATION & PASSWORD RESET TYPES
// ============================================================

export interface AccountActivationPayload {
  activation_token: string;
  password: string;
  confirm_password: string;
}

export interface AccountActivationResponse {
  application_number: string;
  user_id: string;
  username: string;
  role: string;
  activated: boolean;
  message: string;
}

export interface ResendActivationPayload {
  application_number: string;
  applicant_email: string;
}

export interface ResendActivationResponse {
  application_number: string;
  applicant_email: string;
  message: string;
}

export interface PasswordResetRequestPayload {
  email: string;
}

export interface PasswordResetConfirmPayload {
  reset_token: string;
  password: string;
  confirm_password: string;
}


