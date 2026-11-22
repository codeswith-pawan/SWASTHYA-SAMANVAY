import {
  User,
  BedInventory,
  Referral,
  NotificationItem,
  Patient,
  PatientIntakePayload,
  ConditionAssessmentPayload,
  HospitalRecommendation,
  DistrictMetrics,
  DistrictHospital,
  CriticalAlert,
  StateMetrics,
  DistrictSummary,
  CentralMetrics,
  StateSummary,
  OTPRequestPayload,
  OTPRequestResponse,
  OTPVerifyPayload,
  OTPVerifyResponse,
  CreateStateApplicationPayload,
  CreateDistrictApplicationPayload,
  CreateHospitalApplicationPayload,
  ApplicationCreationResponse,
  ApplicantApplication,
  DocumentMetadata,
  SubmitApplicationResponse,
  ResubmitApplicationResponse,
  PublicTrackingData,
  ReviewerApplicationListResponse,
  ReviewerApplicationDetail,
  VerifyDocumentPayload,
  ReviewDecisionPayload,
  ReviewDecisionResponse,
  RequestCorrectionPayload,
  AccountActivationPayload,
  AccountActivationResponse,
  ResendActivationPayload,
  ResendActivationResponse,
  PasswordResetRequestPayload,
  PasswordResetConfirmPayload,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8050";

const TOKEN_KEY = "access_token";
const USER_KEY = "sih_auth_user";
const APPLICANT_TOKEN_KEY = "sih_applicant_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
}

export function getApplicantToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(APPLICANT_TOKEN_KEY);
}

export function setApplicantToken(token: string): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(APPLICANT_TOKEN_KEY, token);
}

export function clearApplicantToken(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(APPLICANT_TOKEN_KEY);
}

export function getStoredUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function setStoredSession(user: User, token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearStoredSession(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

interface ApiErrorPayload {
  detail?: string | { message?: string };
  message?: string;
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (err) {
    throw new ApiError(
      "Unable to connect to healthcare backend service. Please check network connectivity.",
      0,
      err
    );
  }

  let data: unknown = null;
  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    let message = "Request failed.";
    if (data && typeof data === "object") {
      const errObj = data as ApiErrorPayload;
      if (typeof errObj.detail === "string") {
        message = errObj.detail;
      } else if (errObj.detail && typeof errObj.detail.message === "string") {
        message = errObj.detail.message;
      } else if (typeof errObj.message === "string") {
        message = errObj.message;
      }
    }
    throw new ApiError(message, response.status, data);
  }

  return data as T;
}

// ----------------------------------------------------------------------
// Specific Typed API Callers
// ----------------------------------------------------------------------

export async function apiLogin(username: string, password: string) {
  return apiFetch<{
    success: boolean;
    message: string;
    access_token: string;
    token_type: string;
    user: User;
  }>("/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function apiLogout() {
  clearStoredSession();
}

export async function apiGetInventory(hospitalId: string) {
  return apiFetch<{
    success: boolean;
    hospital_id: string;
    inventory?: BedInventory;
    available_beds?: number;
    available_icu_beds?: number;
    reserved_beds?: number;
    reserved_icu_beds?: number;
  }>(`/hospitals/${hospitalId}/inventory`);
}

export async function apiUpdateInventory(
  hospitalId: string,
  data: {
    bed_type?: "GENERAL" | "ICU" | "EMERGENCY";
    total_capacity?: number;
    capacities?: Array<{
      bed_type: "GENERAL" | "ICU" | "EMERGENCY";
      total_capacity: number;
    }>;
  }
) {
  return apiFetch<{
    success: boolean;
    message: string;
    hospital_id: string;
    inventory: BedInventory;
  }>(`/hospitals/${hospitalId}/inventory`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function apiUpdateResources(
  hospitalId: string,
  resources: {
    oxygen_support?: string;
    ventilator?: string;
    ambulance?: string;
    blood_bank?: string;
    emergency_24x7?: string;
  }
) {
  return apiFetch<{
    success: boolean;
    message: string;
    hospital_id: string;
    inventory: BedInventory;
  }>(`/hospitals/${hospitalId}/resources`, {
    method: "PATCH",
    body: JSON.stringify(resources),
  });
}

export async function apiGetHospitalReferrals(
  hospitalId: string,
  scope: "incoming" | "outgoing" | "all" = "incoming"
) {
  return apiFetch<{
    success: boolean;
    hospital_id: string;
    total_referrals: number;
    referrals: Referral[];
  }>(`/hospitals/${hospitalId}/referrals?scope=${scope}`);
}

export async function apiUpdateReferralStatus(
  referralId: string,
  newStatus: string,
  payload?: {
    ambulance_id?: string;
    eta_minutes?: number;
    notes?: string;
    reason?: string;
  }
) {
  return apiFetch<{
    success: boolean;
    referral: Referral;
    reservation?: {
      bed_id?: string;
      bed_type?: string;
      auto_reservation?: boolean;
    };
    message?: string;
  }>(`/referrals/${referralId}/status/${newStatus}`, {
    method: "POST",
    body: JSON.stringify(payload || {}),
  });
}

export async function apiGetNotifications(hospitalId: string) {
  return apiFetch<{
    success: boolean;
    hospital_id: string;
    total: number;
    unread_count: number;
    notifications: NotificationItem[];
  }>(`/hospitals/${hospitalId}/notifications`);
}

export async function apiMarkNotificationRead(
  hospitalId: string,
  notifId: string
) {
  return apiFetch<{ success: boolean }>(
    `/hospitals/${hospitalId}/notifications/${notifId}/read`,
    { method: "POST" }
  );
}

export async function apiMarkAllNotificationsRead(hospitalId: string) {
  return apiFetch<{ success: boolean; marked_count: number }>(
    `/hospitals/${hospitalId}/notifications/read-all`,
    { method: "POST" }
  );
}

// Reviewer & Government In-App Notifications (Phase 4D-2)
export async function apiGetReviewerNotifications(unreadOnly = false) {
  return apiFetch<{
    role: string;
    user_id?: string;
    jurisdiction?: string;
    unread_count: number;
    total_returned: number;
    notifications: NotificationItem[];
  }>(`/api/registration/review/notifications?unread_only=${unreadOnly}`);
}

export async function apiMarkReviewerNotificationRead(notifId: string | number) {
  return apiFetch<{ success: boolean }>(
    `/api/registration/review/notifications/${notifId}/read`,
    { method: "POST" }
  );
}

export async function apiMarkAllReviewerNotificationsRead() {
  return apiFetch<{ success: boolean; marked_count: number }>(
    `/api/registration/review/notifications/read-all`,
    { method: "POST" }
  );
}

// Applicant In-App Notifications (Phase 4D-2)
export async function apiGetApplicantNotifications(unreadOnly = false) {
  return apiFetch<{
    application_id: string;
    unread_count: number;
    total_returned: number;
    notifications: NotificationItem[];
  }>(`/api/registration/applications/notifications?unread_only=${unreadOnly}`);
}

export async function apiMarkApplicantNotificationRead(notifId: string | number) {
  return apiFetch<{ success: boolean }>(
    `/api/registration/applications/notifications/${notifId}/read`,
    { method: "POST" }
  );
}

export async function apiMarkAllApplicantNotificationsRead() {
  return apiFetch<{ success: boolean; marked_count: number }>(
    `/api/registration/applications/notifications/read-all`,
    { method: "POST" }
  );
}

export async function apiGetRecommendations(patientId: string) {
  return apiFetch<{
    success: boolean;
    patient_id: string;
    priority?: string;
    total_hospitals?: number;
    disqualified_hospitals_count?: number;
    referral_required?: string;
    message?: string;
    reason?: string;
    ai_disclaimer?: string;
    hospitals: HospitalRecommendation[];
  }>(`/hospitals?patient_id=${encodeURIComponent(patientId)}`);
}

export async function apiCreateReferral(payload: {
  patient_id: string;
  from_hospital_id: string;
  to_hospital_id: string;
  reason: string;
  priority: string;
  bed_type: string;
}) {
  return apiFetch<{
    success: boolean;
    message?: string;
    referral: Referral;
    reservation?: {
      bed_id?: string;
      bed_type?: string;
      status?: string;
    };
  }>("/referrals", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function apiAdmitPatient(payload: PatientIntakePayload) {
  return apiFetch<{
    success: boolean;
    message: string;
    patient: Patient;
  }>("/api/hospital/patients", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function apiGetHospitalPatients(hospitalId?: string) {
  try {
    return await apiFetch<{
      success: boolean;
      hospital_id: string;
      count: number;
      patients: Patient[];
    }>("/api/hospital/patients");
  } catch {
    return apiFetch<{
      success: boolean;
      hospital_id: string;
      count: number;
      patients: Patient[];
    }>(`/patients/hospital/${hospitalId || "GH00046"}`);
  }
}

export async function apiAssessAndRecommendHospitals(
  patientId: string,
  assessment: ConditionAssessmentPayload
) {
  return apiFetch<{
    success: boolean;
    patient_id: string;
    condition_summary: string;
    urgency: string;
    required_specialty: string;
    required_bed_type: string;
    transport_requirement: string;
    total_hospitals: number;
    hospitals: HospitalRecommendation[];
  }>(`/api/hospital/patients/${encodeURIComponent(patientId)}/recommend-hospitals`, {
    method: "POST",
    body: JSON.stringify(assessment),
  });
}

export async function apiInitiatePatientReferral(
  patientId: string,
  payload: {
    to_hospital_id: string;
    reason: string;
    priority?: string;
    bed_type?: string;
    transport_requirement?: string;
    clinical_condition_snapshot?: Record<string, any>;
  }
) {
  return apiFetch<{
    success: boolean;
    message: string;
    referral: Referral;
  }>(`/api/hospital/patients/${encodeURIComponent(patientId)}/refer`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function apiGetPatientReferrals(patientId: string) {
  return apiFetch<{
    success: boolean;
    patient_id: string;
    total_referrals: number;
    total_system_referrals?: number;
    scope_restricted?: boolean;
    message?: string;
    referrals: Referral[];
  }>(`/patients/${encodeURIComponent(patientId)}/referrals`);
}

// Admin Routes (Phase 4C Unified Government Dashboards)
export async function apiGetDistrictOverview(district?: string, state?: string) {
  const params = new URLSearchParams();
  if (district) params.set("district", district);
  if (state) params.set("state", state);
  const qs = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<{
    success: boolean;
    district: string;
    state: string;
    metrics: DistrictMetrics;
    critical_alerts?: CriticalAlert[];
    hospitals?: DistrictHospital[];
  }>(`/district/overview${qs}`);
}

export async function apiGetDistrictHospitals(params?: {
  district?: string;
  state?: string;
  search?: string;
  status?: string;
  page?: number;
  page_size?: number;
}) {
  const sp = new URLSearchParams();
  if (params?.district) sp.set("district", params.district);
  if (params?.state) sp.set("state", params.state);
  if (params?.search) sp.set("search", params.search);
  if (params?.status) sp.set("status", params.status);
  if (params?.page) sp.set("page", String(params.page));
  if (params?.page_size) sp.set("page_size", String(params.page_size));
  const qs = sp.toString() ? `?${sp.toString()}` : "";
  return apiFetch<{
    success: boolean;
    district: string;
    state: string;
    total: number;
    count: number;
    page: number;
    page_size: number;
    hospitals: DistrictHospital[];
  }>(`/district/hospitals${qs}`);
}

export async function apiGetDistrictReferrals(params?: {
  district?: string;
  state?: string;
  status?: string;
  priority?: string;
  page?: number;
  page_size?: number;
}) {
  const sp = new URLSearchParams();
  if (params?.district) sp.set("district", params.district);
  if (params?.state) sp.set("state", params.state);
  if (params?.status) sp.set("status", params.status);
  if (params?.priority) sp.set("priority", params.priority);
  if (params?.page) sp.set("page", String(params.page));
  if (params?.page_size) sp.set("page_size", String(params.page_size));
  const qs = sp.toString() ? `?${sp.toString()}` : "";
  return apiFetch<{
    success: boolean;
    district: string;
    state: string;
    total: number;
    count: number;
    page: number;
    page_size: number;
    referrals: Referral[];
  }>(`/district/referrals${qs}`);
}

export async function apiGetStateOverview(state?: string) {
  const qs = state ? `?state=${encodeURIComponent(state)}` : "";
  return apiFetch<{
    success: boolean;
    state: string;
    metrics: StateMetrics;
    districts: DistrictSummary[];
  }>(`/state/overview${qs}`);
}

export async function apiGetStateDistricts(state?: string) {
  const qs = state ? `?state=${encodeURIComponent(state)}` : "";
  return apiFetch<{
    success: boolean;
    state: string;
    districts: DistrictSummary[];
  }>(`/state/districts${qs}`);
}

export async function apiGetStateReferrals(params?: {
  state?: string;
  status?: string;
  priority?: string;
  page?: number;
  page_size?: number;
}) {
  const sp = new URLSearchParams();
  if (params?.state) sp.set("state", params.state);
  if (params?.status) sp.set("status", params.status);
  if (params?.priority) sp.set("priority", params.priority);
  if (params?.page) sp.set("page", String(params.page));
  if (params?.page_size) sp.set("page_size", String(params.page_size));
  const qs = sp.toString() ? `?${sp.toString()}` : "";
  return apiFetch<{
    success: boolean;
    state: string;
    total: number;
    count: number;
    page: number;
    page_size: number;
    referrals: Referral[];
  }>(`/state/referrals${qs}`);
}

export async function apiGetStateHospitals(params?: {
  state?: string;
  district?: string;
  search?: string;
  status?: string;
  page?: number;
  page_size?: number;
}) {
  const sp = new URLSearchParams();
  if (params?.state) sp.set("state", params.state);
  if (params?.district) sp.set("district", params.district);
  if (params?.search) sp.set("search", params.search);
  if (params?.status) sp.set("status", params.status);
  if (params?.page) sp.set("page", String(params.page));
  if (params?.page_size) sp.set("page_size", String(params.page_size));
  const qs = sp.toString() ? `?${sp.toString()}` : "";
  return apiFetch<{
    success: boolean;
    state: string;
    total: number;
    count: number;
    page: number;
    page_size: number;
    hospitals: DistrictHospital[];
  }>(`/state/hospitals${qs}`);
}

export async function apiGetCentralOverview() {
  return apiFetch<{
    success: boolean;
    metrics: CentralMetrics;
    states: StateSummary[];
  }>("/central/overview");
}

export async function apiGetCentralStates() {
  return apiFetch<{
    success: boolean;
    states: StateSummary[];
  }>("/central/states");
}

export async function apiGetCentralHospitals(params?: {
  state?: string;
  district?: string;
  search?: string;
  status?: string;
  page?: number;
  page_size?: number;
}) {
  const sp = new URLSearchParams();
  if (params?.state) sp.set("state", params.state);
  if (params?.district) sp.set("district", params.district);
  if (params?.search) sp.set("search", params.search);
  if (params?.status) sp.set("status", params.status);
  if (params?.page) sp.set("page", String(params.page));
  if (params?.page_size) sp.set("page_size", String(params.page_size));
  const qs = sp.toString() ? `?${sp.toString()}` : "";
  return apiFetch<{
    success: boolean;
    total: number;
    count: number;
    page: number;
    page_size: number;
    hospitals: DistrictHospital[];
  }>(`/central/hospitals${qs}`);
}

export async function apiGetCentralReferrals(params?: {
  state?: string;
  district?: string;
  status?: string;
  priority?: string;
  page?: number;
  page_size?: number;
}) {
  const sp = new URLSearchParams();
  if (params?.state) sp.set("state", params.state);
  if (params?.district) sp.set("district", params.district);
  if (params?.status) sp.set("status", params.status);
  if (params?.priority) sp.set("priority", params.priority);
  if (params?.page) sp.set("page", String(params.page));
  if (params?.page_size) sp.set("page_size", String(params.page_size));
  const qs = sp.toString() ? `?${sp.toString()}` : "";
  return apiFetch<{
    success: boolean;
    total: number;
    count: number;
    page: number;
    page_size: number;
    referrals: Referral[];
  }>(`/central/referrals${qs}`);
}

// ============================================================
// APPLICANT & REGISTRATION PORTAL APIS (Phase 1 & Phase 2)
// ============================================================

export async function apiApplicantFetch<T>(
  endpoint: string,
  options: RequestInit = {},
  applicantToken?: string | null
): Promise<T> {
  const token = applicantToken || getApplicantToken();
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (err) {
    throw new ApiError("Failed to reach server. Please check connection.", 0, err);
  }

  if (!response.ok) {
    let payload: ApiErrorPayload | null = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }

    const detailMsg =
      typeof payload?.detail === "string"
        ? payload.detail
        : typeof payload?.detail === "object" && payload?.detail !== null
        ? payload.detail.message
        : payload?.message;

    const message = detailMsg || `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status, payload);
  }

  return response.json();
}

/**
 * Request OTP via Email or SMS for Registration or Portal Access
 */
export async function apiSendRegistrationOTP(
  payload: OTPRequestPayload
): Promise<OTPRequestResponse> {
  return apiFetch<OTPRequestResponse>("/api/registration/auth/otp/request", {
    method: "POST",
    body: JSON.stringify({
      contact_target: payload.contact_target,
      channel: payload.channel || "EMAIL",
      purpose: payload.purpose || "PORTAL_ACCESS_OTP",
      application_number: payload.application_number || undefined,
    }),
  });
}

/**
 * Verify OTP and optionally acquire an applicant session token
 */
export async function apiVerifyRegistrationOTP(
  payload: OTPVerifyPayload
): Promise<OTPVerifyResponse> {
  const res = await apiFetch<OTPVerifyResponse>("/api/registration/auth/otp/verify", {
    method: "POST",
    body: JSON.stringify({
      token_id: payload.token_id,
      otp: payload.otp,
      purpose: payload.purpose || "PORTAL_ACCESS_OTP",
      application_number: payload.application_number || undefined,
    }),
  });

  if (res.applicant_token) {
    setApplicantToken(res.applicant_token);
  }

  return res;
}

/**
 * Register a State Directorate Application
 */
export async function apiCreateStateApplication(
  payload: CreateStateApplicationPayload
): Promise<ApplicationCreationResponse> {
  const res = await apiFetch<ApplicationCreationResponse>(
    "/api/registration/applications/state",
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
  if (res.applicant_token) {
    setApplicantToken(res.applicant_token);
  }
  return res;
}

/**
 * Register a District Health Administration Application
 */
export async function apiCreateDistrictApplication(
  payload: CreateDistrictApplicationPayload
): Promise<ApplicationCreationResponse> {
  const res = await apiFetch<ApplicationCreationResponse>(
    "/api/registration/applications/district",
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
  if (res.applicant_token) {
    setApplicantToken(res.applicant_token);
  }
  return res;
}

/**
 * Register a Hospital / Healthcare Facility Application
 */
export async function apiCreateHospitalApplication(
  payload: CreateHospitalApplicationPayload
): Promise<ApplicationCreationResponse> {
  const res = await apiFetch<ApplicationCreationResponse>(
    "/api/registration/applications/hospital",
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
  if (res.applicant_token) {
    setApplicantToken(res.applicant_token);
  }
  return res;
}

/**
 * Get current authenticated applicant's application details & documents
 */
export async function apiGetMyApplication(
  applicantToken?: string | null
): Promise<ApplicantApplication> {
  return apiApplicantFetch<ApplicantApplication>(
    "/api/registration/applications/me",
    { method: "GET" },
    applicantToken
  );
}

/**
 * Update Draft Profile Data
 */
export async function apiUpdateDraftApplication(
  payload: Record<string, unknown>,
  applicantToken?: string | null
): Promise<ApplicantApplication> {
  return apiApplicantFetch<ApplicantApplication>(
    "/api/registration/applications/draft",
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
    applicantToken
  );
}

/**
 * Upload Multipart Document Binary (PDF, JPEG, PNG <= 25MB)
 */
export async function apiUploadDocument(
  documentType: string,
  file: File,
  applicantToken?: string | null
): Promise<DocumentMetadata> {
  const formData = new FormData();
  formData.append("document_type", documentType);
  formData.append("file", file);

  return apiApplicantFetch<DocumentMetadata>(
    "/api/registration/applications/documents/upload",
    {
      method: "POST",
      body: formData,
    },
    applicantToken
  );
}

/**
 * Delete / Remove an uploaded document from draft / correction-required application
 */
export async function apiDeleteDocument(
  documentId: string,
  applicantToken?: string | null
): Promise<{ message: string; document_id: string }> {
  return apiApplicantFetch<{ message: string; document_id: string }>(
    `/api/registration/applications/documents/${documentId}`,
    {
      method: "DELETE",
    },
    applicantToken
  );
}

/**
 * Submit Draft Application into Verification Pipeline
 */
export async function apiSubmitApplication(
  remarks?: string,
  applicantToken?: string | null
): Promise<SubmitApplicationResponse> {
  return apiApplicantFetch<SubmitApplicationResponse>(
    "/api/registration/applications/submit",
    {
      method: "POST",
      body: JSON.stringify({ remarks: remarks || undefined }),
    },
    applicantToken
  );
}

/**
 * Resubmit Application after corrections
 */
export async function apiResubmitApplication(
  applicantNotes: string,
  applicantToken?: string | null
): Promise<ResubmitApplicationResponse> {
  return apiApplicantFetch<ResubmitApplicationResponse>(
    "/api/registration/applications/resubmit",
    {
      method: "POST",
      body: JSON.stringify({ applicant_notes: applicantNotes }),
    },
    applicantToken
  );
}

/**
 * Public Unauthenticated Application Tracking (Safe milestone data only)
 */
export async function apiPublicTrackApplication(
  applicationNumber: string,
  trackingToken: string
): Promise<PublicTrackingData> {
  const sanitizedApp = encodeURIComponent(applicationNumber.trim());
  const sanitizedToken = encodeURIComponent(trackingToken.trim());
  return apiFetch<PublicTrackingData>(
    `/api/registration/public/track/${sanitizedApp}?tracking_token=${sanitizedToken}`
  );
}

// ============================================================
// PHASE 2D: REVIEWER WORKFLOW APIS
// ============================================================

export interface ReviewerFilterParams {
  status?: string;
  stage?: string;
  applicant_type?: string;
  limit?: number;
  offset?: number;
}

/**
 * Fetch assigned / jurisdiction-scoped applications for authenticated reviewer
 */
export async function apiGetReviewerApplications(
  params: ReviewerFilterParams = {}
): Promise<ReviewerApplicationListResponse> {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.stage) query.set("stage", params.stage);
  if (params.applicant_type) query.set("applicant_type", params.applicant_type);
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.offset !== undefined) query.set("offset", String(params.offset));

  const qs = query.toString();
  return apiFetch<ReviewerApplicationListResponse>(
    `/api/registration/review/applications${qs ? `?${qs}` : ""}`
  );
}

/**
 * Fetch complete application dossier, documents, and audit trail for reviewer
 */
export async function apiGetReviewerApplicationDetail(
  applicationId: string
): Promise<ReviewerApplicationDetail> {
  return apiFetch<ReviewerApplicationDetail>(
    `/api/registration/review/applications/${applicationId}`
  );
}

/**
 * Mark a document as VERIFIED or REJECTED with optional/required remarks
 */
export async function apiVerifyReviewerDocument(
  documentId: string,
  payload: VerifyDocumentPayload
): Promise<{
  document_id: string;
  application_id: string;
  verification_status: string;
  reviewer_remarks?: string | null;
  message: string;
}> {
  return apiFetch<{
    document_id: string;
    application_id: string;
    verification_status: string;
    reviewer_remarks?: string | null;
    message: string;
  }>(`/api/registration/review/documents/${documentId}/verify`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Execute stage transition decision (FORWARD, APPROVE, REJECT)
 */
export async function apiExecuteReviewDecision(
  applicationId: string,
  payload: ReviewDecisionPayload
): Promise<ReviewDecisionResponse> {
  return apiFetch<ReviewDecisionResponse>(
    `/api/registration/review/applications/${applicationId}/decision`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

/**
 * Request specific applicant corrections
 */
export async function apiReviewerRequestCorrection(
  applicationId: string,
  payload: RequestCorrectionPayload
): Promise<{
  application_id: string;
  application_number: string;
  status: string;
  current_stage: string;
  correction_notes: string;
}> {
  return apiFetch<{
    application_id: string;
    application_number: string;
    status: string;
    current_stage: string;
    correction_notes: string;
  }>(`/api/registration/review/applications/${applicationId}/request-correction`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Securely fetch document binary blob for preview or download using caller JWT
 */
export async function apiDownloadDocumentBlob(
  documentId: string
): Promise<{ blob: Blob; filename: string; contentType: string }> {
  const token = getToken();
  const headers = new Headers();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = `${API_BASE}/api/registration/applications/documents/${documentId}/download`;
  const response = await fetch(url, { headers });

  if (!response.ok) {
    throw new ApiError(`Failed to download document (HTTP ${response.status})`, response.status);
  }

  const contentDisposition = response.headers.get("Content-Disposition") || "";
  let filename = `document_${documentId}`;
  const match = contentDisposition.match(/filename="?([^"]+)"?/);
  if (match && match[1]) {
    filename = match[1];
  }

  const blob = await response.blob();
  return { blob, filename, contentType: blob.type || response.headers.get("Content-Type") || "application/octet-stream" };
}

// ============================================================
// PHASE 2D: ACCOUNT ACTIVATION & PASSWORD RESET APIS
// ============================================================

/**
 * Activate operational account using single-use activation token
 */
export async function apiActivateAccount(
  payload: AccountActivationPayload
): Promise<AccountActivationResponse> {
  return apiFetch<AccountActivationResponse>("/api/registration/auth/activate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Resend activation invitation link
 */
export async function apiResendActivation(
  payload: ResendActivationPayload
): Promise<ResendActivationResponse> {
  return apiFetch<ResendActivationResponse>("/api/registration/auth/activation/resend", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Request password recovery link for operational account
 */
export async function apiRequestPasswordReset(
  payload: PasswordResetRequestPayload
): Promise<{ message: string }> {
  return apiFetch<{ message: string }>("/api/registration/auth/password-reset/request", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Confirm password reset using one-time reset token
 */
export async function apiConfirmPasswordReset(
  payload: PasswordResetConfirmPayload
): Promise<{ user_id: string; username: string; message: string }> {
  return apiFetch<{ user_id: string; username: string; message: string }>(
    "/api/registration/auth/password-reset/confirm",
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}


