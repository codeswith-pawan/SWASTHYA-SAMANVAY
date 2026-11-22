"use client";

import React, { useEffect, useState } from "react";
import {
  User,
  BedInventory,
  Referral,
  NotificationItem,
  Patient,
  PatientIntakePayload,
  ConditionAssessmentPayload,
  HospitalRecommendation,
} from "@/lib/types";
import {
  apiGetInventory,
  apiUpdateInventory,
  apiUpdateResources,
  apiGetHospitalReferrals,
  apiUpdateReferralStatus,
  apiGetNotifications,
  apiMarkNotificationRead,
  apiMarkAllNotificationsRead,
  apiGetRecommendations,
  apiCreateReferral,
  apiGetHospitalPatients,
  apiGetPatientReferrals,
  apiAdmitPatient,
  apiAssessAndRecommendHospitals,
  apiInitiatePatientReferral,
} from "@/lib/api";
import { formatDateTime, formatDistance, formatModelFitScore } from "@/lib/formatters";
import { DashboardLayout } from "./shared/DashboardLayout";
import { StatCard } from "./shared/StatCard";
import { StatusBadge, PriorityBadge } from "./shared/StatusBadge";
import { DataTable, Column } from "./shared/DataTable";
import { ReferralTimeline } from "./shared/ReferralTimeline";
import { ConfirmationModal } from "./shared/ConfirmationModal";
import { EmptyState } from "./shared/EmptyState";
import { LoadingState, ErrorState } from "./shared/LoadingAndErrorStates";

interface HospitalDashboardProps {
  user: User;
}

export default function HospitalDashboard({ user }: HospitalDashboardProps) {
  const [activeTab, setActiveTab] = useState("overview");

  // Inventory State
  const [inventory, setInventory] = useState<BedInventory | null>(null);
  const [inventoryLoading, setInventoryLoading] = useState(false);
  const [inventoryError, setInventoryError] = useState("");

  // Referrals State
  const [allReferrals, setAllReferrals] = useState<Referral[]>([]);
  const [referralScope, setReferralScope] = useState<"incoming" | "outgoing" | "all">("incoming");
  const [referralLoading, setReferralLoading] = useState(false);
  const [referralError, setReferralError] = useState("");
  const [selectedReferralForTimeline, setSelectedReferralForTimeline] = useState<Referral | null>(null);
  const [reservationNotice, setReservationNotice] = useState<{
    referralId: string;
    message: string;
  } | null>(null);

  // Status Action Loading & Modals
  const [statusLoading, setStatusLoading] = useState(false);
  const [acceptingId, setAcceptingId] = useState<string | null>(null);

  // Dispatch Ambulance Modal
  const [dispatchModalReferral, setDispatchModalReferral] = useState<Referral | null>(null);
  const [dispatchAmbulanceId, setDispatchAmbulanceId] = useState("AMB-108-ADVANCED");
  const [dispatchEtaMinutes, setDispatchEtaMinutes] = useState(20);
  const [dispatchNotes, setDispatchNotes] = useState("");

  // Reject Referral Modal
  const [rejectModalReferral, setRejectModalReferral] = useState<Referral | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  // Notifications State
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifLoading, setNotifLoading] = useState(false);

  // Patients State
  const [patients, setPatients] = useState<Patient[]>([]);
  const [patientLoading, setPatientLoading] = useState(false);
  const [patientError, setPatientError] = useState("");
  const [selectedPatientForHistory, setSelectedPatientForHistory] = useState<Patient | null>(null);
  const [patientReferrals, setPatientReferrals] = useState<Referral[]>([]);
  const [patientReferralLoading, setPatientReferralLoading] = useState(false);

  // Referral Creation & 2-Step AI Recommendations Modal
  const [referralModalPatient, setReferralModalPatient] = useState<Patient | null>(null);
  const [referralModalStep, setReferralModalStep] = useState<1 | 2>(1);
  const [referralTargetHospitalId, setReferralTargetHospitalId] = useState("");
  const [referralPriority, setReferralPriority] = useState("Urgent");
  const [referralBedType, setReferralBedType] = useState<"ICU" | "GENERAL" | "EMERGENCY">("GENERAL");
  const [referralReason, setReferralReason] = useState("");
  const [recommendations, setRecommendations] = useState<HospitalRecommendation[]>([]);
  const [recLoading, setRecLoading] = useState(false);
  const [recError, setRecError] = useState("");
  const [createReferralLoading, setCreateReferralLoading] = useState(false);
  const [createReferralError, setCreateReferralError] = useState("");
  const [createReferralSuccess, setCreateReferralSuccess] = useState("");

  // Step 1 Clinical Condition Assessment State
  const [evalConditionSummary, setEvalConditionSummary] = useState("");
  const [evalUrgency, setEvalUrgency] = useState<"ROUTINE" | "URGENT" | "EMERGENCY" | "CRITICAL">("URGENT");
  const [evalSpecialty, setEvalSpecialty] = useState("Cardiology");
  const [evalBedType, setEvalBedType] = useState<"GENERAL" | "ICU" | "VENTILATOR" | "EMERGENCY" | "NICU">("ICU");
  const [evalTransport, setEvalTransport] = useState<"NONE" | "BASIC_AMBULANCE" | "ALS_AMBULANCE">("ALS_AMBULANCE");
  const [evalHeartRate, setEvalHeartRate] = useState<number | "">("");
  const [evalSystolicBP, setEvalSystolicBP] = useState<number | "">("");
  const [evalDiastolicBP, setEvalDiastolicBP] = useState<number | "">("");
  const [evalSpO2, setEvalSpO2] = useState<number | "">("");
  const [evalTemp, setEvalTemp] = useState<number | "">("");
  const [evalRespRate, setEvalRespRate] = useState<number | "">("");
  const [evalGCS, setEvalGCS] = useState<number | "">("");

  // New Patient Intake Modal State
  const [intakeModalOpen, setIntakeModalOpen] = useState(false);
  const [intakeLoading, setIntakeLoading] = useState(false);
  const [intakeError, setIntakeError] = useState("");
  const [intakeSuccessNotice, setIntakeSuccessNotice] = useState("");

  // Intake Form Fields
  const [intakeName, setIntakeName] = useState("");
  const [intakeAge, setIntakeAge] = useState<number | "">("");
  const [intakeGender, setIntakeGender] = useState("Male");
  const [intakeBloodGroup, setIntakeBloodGroup] = useState("B+");
  const [intakePhone, setIntakePhone] = useState("");
  const [intakeEmergencyContact, setIntakeEmergencyContact] = useState("");
  const [intakeAddress, setIntakeAddress] = useState("");
  const [intakeDistrict, setIntakeDistrict] = useState(user.district || "Amritsar");
  const [intakeState, setIntakeState] = useState(user.state || "Punjab");
  const [intakeChiefComplaint, setIntakeChiefComplaint] = useState("");
  const [intakeSpecialty, setIntakeSpecialty] = useState("Cardiology");
  const [intakeBedType, setIntakeBedType] = useState<"GENERAL" | "ICU" | "VENTILATOR" | "OXYGEN" | "EMERGENCY_BAY">("GENERAL");
  const [intakeSeverity, setIntakeSeverity] = useState<"LOW" | "MODERATE" | "HIGH" | "CRITICAL">("MODERATE");
  const [intakeHeartRate, setIntakeHeartRate] = useState<number | "">("");
  const [intakeSystolicBP, setIntakeSystolicBP] = useState<number | "">("");
  const [intakeDiastolicBP, setIntakeDiastolicBP] = useState<number | "">("");
  const [intakeSpO2, setIntakeSpO2] = useState<number | "">("");
  const [intakeTemp, setIntakeTemp] = useState<number | "">("");
  const [intakeRespRate, setIntakeRespRate] = useState<number | "">("");
  const [intakeGCS, setIntakeGCS] = useState<number | "">("");
  const [intakeNotes, setIntakeNotes] = useState("");

  // Bed & Resource Capacity Management State
  const [capacityModalOpen, setCapacityModalOpen] = useState(false);
  const [capGeneral, setCapGeneral] = useState(0);
  const [capICU, setCapICU] = useState(0);
  const [capEmergency, setCapEmergency] = useState(0);
  const [resOxygen, setResOxygen] = useState("Yes");
  const [resVentilator, setResVentilator] = useState("Yes");
  const [resAmbulance, setResAmbulance] = useState("Yes");
  const [resBloodBank, setResBloodBank] = useState("Yes");
  const [resEmergency24x7, setResEmergency24x7] = useState("Yes");
  const [capSaving, setCapSaving] = useState(false);
  const [capModalError, setCapModalError] = useState("");
  const [capModalSuccess, setCapModalSuccess] = useState("");

  const hospitalId = user.hospital_id || "GH00046";

  // Data Loaders
  const loadInventory = async () => {
    setInventoryLoading(true);
    setInventoryError("");
    try {
      const data = await apiGetInventory(hospitalId);
      const invData = (data.inventory || data) as BedInventory;
      setInventory({
        ...invData,
        hospital_id: invData.hospital_id || hospitalId,
        available_beds: Number(invData.available_beds ?? 0),
        available_icu_beds: Number(invData.available_icu_beds ?? 0),
        reserved_beds: Number(invData.reserved_beds ?? 0),
        reserved_icu_beds: Number(invData.reserved_icu_beds ?? 0),
        total_beds: Number(invData.total_beds ?? invData.total_general_beds ?? 0),
        total_general_beds: Number(invData.total_general_beds ?? invData.total_beds ?? 0),
        total_icu_beds: Number(invData.total_icu_beds ?? 0),
        total_emergency_beds: Number(invData.total_emergency_beds ?? 0),
        available_emergency_beds: Number(invData.available_emergency_beds ?? 0),
        reserved_emergency_beds: Number(invData.reserved_emergency_beds ?? 0),
        occupied_emergency_beds: Number(invData.occupied_emergency_beds ?? 0),
        total_available_beds: Number(invData.total_available_beds ?? 0),
        total_reserved_beds: Number(invData.total_reserved_beds ?? 0),
        total_occupied_beds: Number(invData.total_occupied_beds ?? 0),
        total_capacity: Number(invData.total_capacity ?? 0),
        oxygen_support: invData.oxygen_support || "Yes",
        ventilator: invData.ventilator || "Yes",
        ambulance: invData.ambulance || "Yes",
        blood_bank: invData.blood_bank || "Yes",
        emergency_24x7: invData.emergency_24x7 || "Yes",
      });
    } catch (err: any) {
      setInventoryError(err.message || "Failed to load hospital bed inventory.");
    } finally {
      setInventoryLoading(false);
    }
  };

  const openCapacityModal = () => {
    setCapModalError("");
    setCapModalSuccess("");
    const genTotal = inventory?.total_general_beds ?? inventory?.total_beds ?? 0;
    const icuTotal = inventory?.total_icu_beds ?? 0;
    const emgTotal = inventory?.total_emergency_beds ?? 0;
    setCapGeneral(genTotal);
    setCapICU(icuTotal);
    setCapEmergency(emgTotal);
    setResOxygen(inventory?.oxygen_support || "Yes");
    setResVentilator(inventory?.ventilator || "Yes");
    setResAmbulance(inventory?.ambulance || "Yes");
    setResBloodBank(inventory?.blood_bank || "Yes");
    setResEmergency24x7(inventory?.emergency_24x7 || "Yes");
    setCapacityModalOpen(true);
  };

  const handleSaveCapacityAndResources = async () => {
    setCapSaving(true);
    setCapModalError("");
    setCapModalSuccess("");
    try {
      if (capGeneral < 0 || capICU < 0 || capEmergency < 0) {
        throw new Error("Bed capacities cannot be negative.");
      }
      await apiUpdateInventory(hospitalId, {
        capacities: [
          { bed_type: "GENERAL", total_capacity: Number(capGeneral) },
          { bed_type: "ICU", total_capacity: Number(capICU) },
          { bed_type: "EMERGENCY", total_capacity: Number(capEmergency) },
        ],
      });

      await apiUpdateResources(hospitalId, {
        oxygen_support: resOxygen,
        ventilator: resVentilator,
        ambulance: resAmbulance,
        blood_bank: resBloodBank,
        emergency_24x7: resEmergency24x7,
      });

      setCapModalSuccess("Hospital bed inventory and resources successfully updated in PostgreSQL.");
      await loadInventory();
      setTimeout(() => {
        setCapacityModalOpen(false);
      }, 1200);
    } catch (err: any) {
      setCapModalError(err.message || "Failed to update hospital capacity.");
    } finally {
      setCapSaving(false);
    }
  };

  const loadReferrals = async () => {
    setReferralLoading(true);
    setReferralError("");
    try {
      const data = await apiGetHospitalReferrals(hospitalId, "all");
      const fetched = data.referrals || [];
      setAllReferrals(fetched);
    } catch (err: any) {
      setReferralError(err.message || "Failed to load hospital referral roster.");
    } finally {
      setReferralLoading(false);
    }
  };

  const loadNotifications = async () => {
    setNotifLoading(true);
    try {
      const data = await apiGetNotifications(hospitalId);
      setNotifications(data.notifications || []);
      setUnreadCount(data.unread_count || 0);
    } catch {
      // Background poll failure
    } finally {
      setNotifLoading(false);
    }
  };

  const loadPatients = async () => {
    setPatientLoading(true);
    setPatientError("");
    try {
      const data = await apiGetHospitalPatients(hospitalId);
      setPatients(data.patients || []);
    } catch (err: any) {
      setPatientError(err.message || "Failed to load admitted hospital patient list.");
    } finally {
      setPatientLoading(false);
    }
  };

  const refreshAll = () => {
    loadInventory();
    loadReferrals();
    loadNotifications();
    loadPatients();
  };

  useEffect(() => {
    refreshAll();
  }, [hospitalId]);

  // Automatically default to Outbound Referrals if hospital has only outbound cases
  useEffect(() => {
    const inCount = allReferrals.filter(
      (r) => r.to_hospital_id?.toLowerCase() === hospitalId?.toLowerCase()
    ).length;
    const outCount = allReferrals.filter(
      (r) => r.from_hospital_id?.toLowerCase() === hospitalId?.toLowerCase()
    ).length;
    if (inCount === 0 && outCount > 0 && referralScope === "incoming") {
      setReferralScope("outgoing");
    }
  }, [allReferrals, hospitalId, referralScope]);

  // Status Transitions
  const handleUpdateStatus = async (
    referralId: string,
    newStatus: string,
    payload?: { ambulance_id?: string; eta_minutes?: number; notes?: string; reason?: string }
  ) => {
    setStatusLoading(true);
    setReferralError("");
    setReservationNotice(null);
    if (newStatus === "ACCEPTED") setAcceptingId(referralId);

    try {
      const res = await apiUpdateReferralStatus(referralId, newStatus, payload);

      if (newStatus === "ACCEPTED" && res.reservation) {
        const r = res.reservation;
        setReservationNotice({
          referralId,
          message: r.bed_id
            ? `Bed ${r.bed_id} (${r.bed_type || "ICU"}) reserved automatically.`
            : "Bed reservation confirmed in inventory.",
        });
      }

      await loadReferrals();
      await loadInventory();
      await loadNotifications();
      await loadPatients();
    } catch (err: any) {
      setReferralError(err.message || "Failed to execute referral status transition.");
    } finally {
      setStatusLoading(false);
      setAcceptingId(null);
    }
  };

  // Ambulance Dispatch Action
  const confirmDispatch = async () => {
    if (!dispatchModalReferral) return;
    await handleUpdateStatus(dispatchModalReferral.referral_id, "IN_TRANSIT", {
      ambulance_id: dispatchAmbulanceId.trim(),
      eta_minutes: Number(dispatchEtaMinutes) || 15,
      notes: dispatchNotes.trim(),
    });
    setDispatchModalReferral(null);
  };

  // Rejection Action
  const confirmReject = async () => {
    if (!rejectModalReferral) return;
    await handleUpdateStatus(rejectModalReferral.referral_id, "REJECTED", {
      reason: rejectReason.trim() || "Clinical capacity or specialty mismatch.",
    });
    setRejectModalReferral(null);
    setRejectReason("");
  };

  // New Patient Intake Handlers
  const openIntakeModal = () => {
    setIntakeName("");
    setIntakeAge("");
    setIntakeGender("Male");
    setIntakeBloodGroup("B+");
    setIntakePhone("");
    setIntakeEmergencyContact("");
    setIntakeAddress("");
    setIntakeDistrict(user.district || "Amritsar");
    setIntakeState(user.state || "Punjab");
    setIntakeChiefComplaint("");
    setIntakeSpecialty("Cardiology");
    setIntakeBedType("GENERAL");
    setIntakeSeverity("MODERATE");
    setIntakeHeartRate("");
    setIntakeSystolicBP("");
    setIntakeDiastolicBP("");
    setIntakeSpO2("");
    setIntakeTemp("");
    setIntakeRespRate("");
    setIntakeGCS("");
    setIntakeNotes("");
    setIntakeError("");
    setIntakeSuccessNotice("");
    setIntakeModalOpen(true);
  };

  const submitPatientIntake = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!intakeName.trim()) {
      setIntakeError("Patient Full Name is required.");
      return;
    }
    if (intakeAge === "" || Number(intakeAge) < 0 || Number(intakeAge) > 130) {
      setIntakeError("Please provide a valid patient age (0-130).");
      return;
    }
    if (!intakeChiefComplaint.trim()) {
      setIntakeError("Chief Complaint / Primary Diagnosis is required.");
      return;
    }

    setIntakeLoading(true);
    setIntakeError("");
    setIntakeSuccessNotice("");

    const payload: PatientIntakePayload = {
      name: intakeName.trim(),
      age: Number(intakeAge),
      gender: intakeGender,
      blood_group: intakeBloodGroup,
      contact_phone: intakePhone.trim() || undefined,
      emergency_contact: intakeEmergencyContact.trim() || undefined,
      address: intakeAddress.trim() || undefined,
      district: intakeDistrict.trim() || undefined,
      state: intakeState.trim() || undefined,
      chief_complaint: intakeChiefComplaint.trim(),
      required_specialty: intakeSpecialty,
      bed_type_assigned: intakeBedType,
      severity_level: intakeSeverity,
      vitals: {
        heart_rate: intakeHeartRate ? Number(intakeHeartRate) : undefined,
        systolic_bp: intakeSystolicBP ? Number(intakeSystolicBP) : undefined,
        diastolic_bp: intakeDiastolicBP ? Number(intakeDiastolicBP) : undefined,
        blood_pressure: intakeSystolicBP && intakeDiastolicBP ? `${intakeSystolicBP}/${intakeDiastolicBP}` : undefined,
        spo2: intakeSpO2 ? Number(intakeSpO2) : undefined,
        temperature: intakeTemp ? Number(intakeTemp) : undefined,
        respiratory_rate: intakeRespRate ? Number(intakeRespRate) : undefined,
        gcs_score: intakeGCS ? Number(intakeGCS) : undefined,
      },
      clinical_notes: intakeNotes.trim() || undefined,
    };

    try {
      const res = await apiAdmitPatient(payload);
      const generatedId = res.patient.patient_id;
      setIntakeSuccessNotice(`Patient admitted successfully with Official Patient ID: ${generatedId}`);
      await loadPatients();
      await loadInventory();
      setTimeout(() => {
        setIntakeModalOpen(false);
        setActiveTab("patients");
      }, 1500);
    } catch (err: any) {
      setIntakeError(err.message || "Failed to register patient admission.");
    } finally {
      setIntakeLoading(false);
    }
  };

  // Referral Creation & 2-Step AI Recommendations
  const openReferralModal = (patient: Patient) => {
    setReferralModalPatient(patient);
    setReferralModalStep(1); // Step 1: Current Clinical Condition Assessment
    setReferralTargetHospitalId("");

    // Pre-fill doctor's assessment from patient's known records
    setEvalConditionSummary(
      patient.chief_complaint || patient.disease
        ? `Patient admitted with ${patient.chief_complaint || patient.disease}. Evaluated for specialized inter-facility transfer.`
        : ""
    );
    setEvalUrgency(
      patient.priority === "Critical" ? "CRITICAL" : patient.priority === "Urgent" ? "URGENT" : "ROUTINE"
    );
    setEvalSpecialty(patient.required_specialty || "Cardiology");
    setEvalBedType(patient.icu_required === "Yes" || patient.bed_type === "ICU" ? "ICU" : "GENERAL");
    setEvalTransport(patient.priority === "Critical" ? "ALS_AMBULANCE" : "NONE");

    const v = patient.vitals || {};
    setEvalHeartRate(v.heart_rate || "");
    setEvalSystolicBP(v.systolic_bp || "");
    setEvalDiastolicBP(v.diastolic_bp || "");
    setEvalSpO2(v.spo2 || "");
    setEvalTemp(v.temperature || "");
    setEvalRespRate(v.respiratory_rate || "");
    setEvalGCS(v.gcs_score || "");

    setRecommendations([]);
    setRecError("");
    setCreateReferralError("");
    setCreateReferralSuccess("");
  };

  const handleRunConditionAssessment = async () => {
    if (!referralModalPatient) return;
    if (!evalConditionSummary.trim()) {
      setRecError("Please provide a Current Clinical Condition Assessment / Reason for Referral.");
      return;
    }
    setRecLoading(true);
    setRecError("");

    const assessment: ConditionAssessmentPayload = {
      condition_summary: evalConditionSummary.trim(),
      urgency: evalUrgency,
      required_specialty: evalSpecialty,
      required_bed_type: evalBedType,
      transport_requirement: evalTransport,
      vitals: {
        heart_rate: evalHeartRate ? Number(evalHeartRate) : undefined,
        systolic_bp: evalSystolicBP ? Number(evalSystolicBP) : undefined,
        diastolic_bp: evalDiastolicBP ? Number(evalDiastolicBP) : undefined,
        blood_pressure: evalSystolicBP && evalDiastolicBP ? `${evalSystolicBP}/${evalDiastolicBP}` : undefined,
        spo2: evalSpO2 ? Number(evalSpO2) : undefined,
        temperature: evalTemp ? Number(evalTemp) : undefined,
        respiratory_rate: evalRespRate ? Number(evalRespRate) : undefined,
        gcs_score: evalGCS ? Number(evalGCS) : undefined,
      },
    };

    try {
      const data = await apiAssessAndRecommendHospitals(referralModalPatient.patient_id, assessment);
      setRecommendations(data.hospitals || []);
      if (data.hospitals && data.hospitals.length > 0) {
        setReferralTargetHospitalId(data.hospitals[0].hospital_id);
      }
      setReferralModalStep(2); // Advance to Step 2: AI-Ranked Suitable Destination Hospitals
    } catch (err: any) {
      setRecError(err.message || "Failed to calculate AI-ranked hospital recommendations.");
    } finally {
      setRecLoading(false);
    }
  };

  const submitCreateReferral = async () => {
    if (!referralModalPatient) return;
    if (!referralTargetHospitalId.trim()) {
      setCreateReferralError("Please select a destination hospital from the AI recommendations.");
      return;
    }
    setCreateReferralLoading(true);
    setCreateReferralError("");
    setCreateReferralSuccess("");

    try {
      const res = await apiInitiatePatientReferral(referralModalPatient.patient_id, {
        to_hospital_id: referralTargetHospitalId.trim().toUpperCase(),
        reason: evalConditionSummary.trim() || `Clinical transfer for ${evalSpecialty}`,
        priority: evalUrgency === "CRITICAL" ? "Critical" : evalUrgency === "URGENT" ? "Urgent" : "Stable",
        bed_type: evalBedType,
        transport_requirement: evalTransport,
        clinical_condition_snapshot: {
          specialty: evalSpecialty,
          vitals: {
            spo2: evalSpO2,
            heart_rate: evalHeartRate,
            bp: `${evalSystolicBP}/${evalDiastolicBP}`,
          },
        },
      });

      setCreateReferralSuccess(
        `Referral ${res.referral?.referral_id || ""} successfully created and dispatched to destination hospital queue!`
      );
      setTimeout(() => {
        setReferralModalPatient(null);
        setActiveTab("referrals");
        setReferralScope("outgoing");
        loadReferrals();
        loadPatients();
        loadNotifications();
      }, 1400);
    } catch (err: any) {
      setCreateReferralError(err.message || "Failed to initiate network referral.");
    } finally {
      setCreateReferralLoading(false);
    }
  };

  // Patient Referral History Drawer
  const openPatientHistory = async (patient: Patient) => {
    setSelectedPatientForHistory(patient);
    setPatientReferralLoading(true);
    try {
      const data = await apiGetPatientReferrals(patient.patient_id);
      setPatientReferrals(data.referrals || []);
    } catch {
      setPatientReferrals([]);
    } finally {
      setPatientReferralLoading(false);
    }
  };

  // Computed Metrics & Roster Slices
  const inboundReferrals = allReferrals.filter(
    (r) => r.to_hospital_id?.toLowerCase() === hospitalId?.toLowerCase()
  );
  const outboundReferrals = allReferrals.filter(
    (r) => r.from_hospital_id?.toLowerCase() === hospitalId?.toLowerCase()
  );
  const displayedReferrals =
    referralScope === "incoming"
      ? inboundReferrals
      : referralScope === "outgoing"
      ? outboundReferrals
      : allReferrals;

  const activeReferralsCount = allReferrals.filter(
    (r) => !["COMPLETED", "REJECTED", "DIED", "CLOSED"].includes(r.status)
  ).length;

  const pendingIncomingCount = inboundReferrals.filter((r) => r.status === "PENDING").length;

  const inTransitCount = allReferrals.filter((r) => r.status === "IN_TRANSIT").length;

  // Referral Columns Definition for DataTable
  const referralColumns: Column<Referral>[] = [
    {
      key: "referral_id",
      header: "Case ID",
      render: (r) => (
        <div>
          <span className="font-mono font-bold text-blue-400">{r.referral_id}</span>
          <p className="text-[10px] text-slate-400">{r.patient_id}</p>
        </div>
      ),
    },
    {
      key: "direction",
      header: "Route",
      render: (r) => {
        const isIncoming = r.to_hospital_id?.toLowerCase() === hospitalId?.toLowerCase();
        return (
          <div className="space-y-0.5">
            <span
              className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-bold ${
                isIncoming
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
              }`}
            >
              {isIncoming ? "INBOUND" : "OUTBOUND"}
            </span>
            <p className="text-[11px] text-slate-300">
              {isIncoming ? `From: ${r.from_hospital_id}` : `To: ${r.to_hospital_id}`}
            </p>
          </div>
        );
      },
    },
    {
      key: "priority",
      header: "Priority",
      render: (r) => <PriorityBadge priority={r.priority} size="sm" />,
    },
    {
      key: "bed_type",
      header: "Bed Reqd",
      render: (r) => (
        <span className="font-semibold text-slate-200">
          {r.bed_type || (r.reason?.toLowerCase().includes("icu") ? "ICU" : "GENERAL")}
        </span>
      ),
    },
    {
      key: "status",
      header: "Current Stage",
      render: (r) => <StatusBadge status={r.status} size="sm" />,
    },
    {
      key: "created_at",
      header: "Initiated",
      render: (r) => (
        <span className="font-mono text-[11px] text-slate-400">
          {formatDateTime(r.created_at)}
        </span>
      ),
    },
    {
      key: "actions",
      header: "Operational Actions",
      align: "right",
      render: (r) => {
        const isDestination = r.to_hospital_id?.toLowerCase() === hospitalId?.toLowerCase();
        const isSource = r.from_hospital_id?.toLowerCase() === hospitalId?.toLowerCase();
        const isBusy = statusLoading;

        return (
          <div className="flex items-center justify-end gap-1.5 flex-wrap">
            {/* INCOMING PENDING -> ACCEPT / REJECT */}
            {isDestination && r.status === "PENDING" && (
              <>
                <button
                  onClick={() => handleUpdateStatus(r.referral_id, "ACCEPTED")}
                  disabled={isBusy}
                  className="rounded-lg bg-emerald-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-emerald-500 disabled:opacity-50 transition"
                  title="Accept referral and reserve bed automatically"
                >
                  {acceptingId === r.referral_id ? "Reserving..." : "✓ Accept & Reserve"}
                </button>
                <button
                  onClick={() => setRejectModalReferral(r)}
                  disabled={isBusy}
                  className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-2.5 py-1 text-[11px] font-semibold text-rose-300 hover:bg-rose-500/20 disabled:opacity-50 transition"
                  title="Decline referral"
                >
                  ✕ Reject
                </button>
              </>
            )}

            {/* OUTGOING ACCEPTED -> DISPATCH AMBULANCE */}
            {isSource && r.status === "ACCEPTED" && (
              <button
                onClick={() => setDispatchModalReferral(r)}
                disabled={isBusy}
                className="rounded-lg bg-blue-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-blue-500 disabled:opacity-50 transition"
                title="Dispatch ambulance and enter ETA"
              >
                🚑 Dispatch Ambulance
              </button>
            )}

            {/* INCOMING IN_TRANSIT or ACCEPTED -> CONFIRM ARRIVAL */}
            {isDestination && (r.status === "IN_TRANSIT" || r.status === "ACCEPTED") && (
              <button
                onClick={() => handleUpdateStatus(r.referral_id, "ARRIVED")}
                disabled={isBusy}
                className="rounded-lg bg-cyan-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-cyan-500 disabled:opacity-50 transition"
                title="Confirm patient arrived at emergency bay"
              >
                🏥 Confirm Arrival
              </button>
            )}

            {/* INCOMING ARRIVED -> COMMENCE TREATMENT */}
            {isDestination && r.status === "ARRIVED" && (
              <button
                onClick={() => handleUpdateStatus(r.referral_id, "TREATMENT_ACTIVE")}
                disabled={isBusy}
                className="rounded-lg bg-purple-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-purple-500 disabled:opacity-50 transition"
                title="Admit to bed and start treatment"
              >
                🩺 Begin Treatment
              </button>
            )}

            {/* INCOMING TREATMENT_ACTIVE or IN_TREATMENT -> COMPLETE & RELEASE BED */}
            {isDestination && (r.status === "TREATMENT_ACTIVE" || r.status === "IN_TREATMENT") && (
              <button
                onClick={() => handleUpdateStatus(r.referral_id, "COMPLETED")}
                disabled={isBusy}
                className="rounded-lg bg-emerald-700 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-emerald-600 disabled:opacity-50 transition"
                title="Complete care and return reserved bed to inventory"
              >
                ✅ Complete & Release Bed
              </button>
            )}

            {/* VIEW TIMELINE BUTTON */}
            <button
              onClick={() => setSelectedReferralForTimeline(r)}
              className="rounded-lg border border-slate-700 bg-slate-800 px-2 py-1 text-[11px] text-slate-300 hover:bg-slate-700 transition"
              title="Inspect lifecycle audit timeline"
            >
              Timeline
            </button>
          </div>
        );
      },
    },
  ];

  // Patients Columns Definition
  const patientColumns: Column<Patient>[] = [
    {
      key: "patient_id",
      header: "Patient ID",
      render: (p) => (
        <div>
          <span className="font-mono font-bold text-blue-400 text-xs block">{p.patient_id}</span>
          <span className="text-[10px] text-slate-400">
            {p.admitted_at ? formatDateTime(p.admitted_at).split(" ")[0] : "Active"}
          </span>
        </div>
      ),
    },
    {
      key: "name",
      header: "Patient Demographics",
      render: (p) => (
        <div>
          <p className="font-semibold text-white">{p.name}</p>
          <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
            <span>{p.age}y • {p.gender}</span>
            {p.blood_group && (
              <span className="rounded bg-rose-500/20 px-1 py-0.2 text-[10px] font-bold text-rose-300">
                {p.blood_group}
              </span>
            )}
          </div>
          {p.contact_phone && (
            <p className="text-[10px] text-slate-500">{p.contact_phone}</p>
          )}
        </div>
      ),
    },
    {
      key: "disease",
      header: "Diagnosis & Specialty",
      render: (p) => (
        <div>
          <span className="text-slate-200 text-xs font-medium block">
            {p.chief_complaint || p.disease}
          </span>
          {p.required_specialty && (
            <span className="inline-block mt-0.5 rounded bg-blue-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-blue-400 border border-blue-500/20">
              {p.required_specialty}
            </span>
          )}
        </div>
      ),
    },
    {
      key: "vitals",
      header: "Vitals & Severity",
      render: (p) => {
        const v = p.vitals || {};
        return (
          <div className="space-y-1">
            <div className="flex items-center gap-1.5">
              <PriorityBadge priority={p.priority} size="sm" />
            </div>
            {(v.spo2 || v.heart_rate) && (
              <div className="text-[10px] font-mono flex items-center gap-2">
                {v.spo2 && (
                  <span className={v.spo2 < 94 ? "text-rose-400 font-bold" : "text-emerald-400"}>
                    SpO2: {v.spo2}%
                  </span>
                )}
                {v.heart_rate && (
                  <span className="text-slate-300">
                    HR: {v.heart_rate} bpm
                  </span>
                )}
              </div>
            )}
          </div>
        );
      },
    },
    {
      key: "bed_type",
      header: "Bed Assigned",
      render: (p) => {
        const b = p.bed_type || (p.icu_required === "Yes" ? "ICU" : "GENERAL");
        const isICU = b === "ICU" || b === "VENTILATOR";
        return (
          <span
            className={`font-semibold text-[11px] px-2 py-0.5 rounded-full inline-block ${
              isICU
                ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                : "bg-slate-800 text-slate-300 border border-slate-700"
            }`}
          >
            {b}
          </span>
        );
      },
    },
    {
      key: "referral_status",
      header: "Referral Status",
      render: (p) => {
        const status = p.referral_status || "NOT_REFERRED";
        if (status === "NOT_REFERRED") {
          return (
            <span className="rounded-full bg-slate-800/80 px-2 py-0.5 text-[10px] font-medium text-slate-400 border border-slate-700/60">
              Not Referred
            </span>
          );
        }
        return <StatusBadge status={status} size="sm" />;
      },
    },
    {
      key: "actions",
      header: "Clinical Workflow",
      align: "right",
      render: (p) => {
        const matchingAcceptedRef = allReferrals.find(
          (r) =>
            r.patient_id === p.patient_id &&
            r.from_hospital_id?.toLowerCase() === hospitalId?.toLowerCase() &&
            r.status === "ACCEPTED"
        );
        const matchingInTransitRef = allReferrals.find(
          (r) =>
            r.patient_id === p.patient_id &&
            r.from_hospital_id?.toLowerCase() === hospitalId?.toLowerCase() &&
            r.status === "IN_TRANSIT"
        );

        return (
          <div className="flex items-center justify-end gap-2">
            {matchingAcceptedRef ? (
              <button
                onClick={() => setDispatchModalReferral(matchingAcceptedRef)}
                className="flex items-center gap-1 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-amber-500 shadow-md shadow-amber-600/20 transition active:scale-95"
                title="Referral accepted by destination facility. Click to dispatch ambulance."
              >
                <span>🚑 Dispatch</span>
              </button>
            ) : matchingInTransitRef ? (
              <span className="rounded-lg bg-cyan-950/80 border border-cyan-800/80 px-2.5 py-1 text-[11px] font-semibold text-cyan-300">
                En Route 🚑
              </span>
            ) : (
              <button
                onClick={() => openReferralModal(p)}
                className="flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-blue-500 shadow-md shadow-blue-600/20 transition active:scale-95"
                title="Evaluate clinical condition and launch AI-ranked destination referrals"
              >
                <span>Refer Patient</span>
                <span>→</span>
              </button>
            )}
            <button
              onClick={() => openPatientHistory(p)}
              className="rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 transition"
              title="View referral history across network"
            >
              History
            </button>
          </div>
        );
      },
    },
  ];

  return (
    <DashboardLayout
      user={user}
      tierBadge={{ label: "Hospital Clinical Command", color: "blue" }}
      title={user.name || `Hospital Facility ${hospitalId}`}
      subtitle={`Facility ID: ${hospitalId} • Jurisdiction: ${user.district || "Amritsar"}, ${user.state || "Punjab"}`}
      headerAction={
        <button
          onClick={openIntakeModal}
          className="flex items-center gap-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white px-3.5 py-2 text-xs font-bold shadow-lg shadow-blue-600/25 transition active:scale-95"
          title="Admit fresh patient into clinical registry"
        >
          <span className="text-base font-bold leading-none">+</span>
          <span className="hidden sm:inline">Register New Patient</span>
          <span className="sm:hidden">Intake</span>
        </button>
      }
      tabs={[
        { id: "overview", label: "Operations Overview", icon: "📊" },
        { id: "referrals", label: "Referrals Command", icon: "🔄", badge: activeReferralsCount },
        { id: "inventory", label: "Bed & Resource Inventory", icon: "🛏️" },
        { id: "patients", label: "Admitted Inpatients", icon: "👥", badge: patients.length },
      ]}
      activeTab={activeTab}
      onTabChange={setActiveTab}
      onRefresh={refreshAll}
      refreshLoading={inventoryLoading || referralLoading}
      notifications={notifications}
      unreadCount={unreadCount}
      notifLoading={notifLoading}
      onMarkNotifRead={(nid) => {
        apiMarkNotificationRead(hospitalId, nid).then(loadNotifications);
      }}
      onMarkAllNotifsRead={() => {
        apiMarkAllNotificationsRead(hospitalId).then(loadNotifications);
      }}
    >
      {/* Notice Banner */}
      {reservationNotice && (
        <div className="mb-6 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-xs text-emerald-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-base">✓</span>
            <span className="font-semibold">{reservationNotice.message}</span>
          </div>
          <button
            onClick={() => setReservationNotice(null)}
            className="text-emerald-400 hover:text-white"
          >
            ✕
          </button>
        </div>
      )}

      {referralError && (
        <ErrorState
          title="Referral Operations Notice"
          message={referralError}
          onRetry={() => loadReferrals()}
          className="mb-6"
        />
      )}

      {/* ============================================================ */}
      {/* TAB 1: OPERATIONS OVERVIEW */}
      {/* ============================================================ */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Top KPI Metrics Grid */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard
              title="Available General Beds"
              value={inventory?.available_beds ?? "—"}
              subtitle={`Reserved: ${inventory?.reserved_beds ?? 0}`}
              icon="🛏️"
              variant="primary"
            />
            <StatCard
              title="Available ICU Beds"
              value={inventory?.available_icu_beds ?? "—"}
              subtitle={`Reserved: ${inventory?.reserved_icu_beds ?? 0}`}
              icon="⚡"
              variant={Number(inventory?.available_icu_beds) > 0 ? "success" : "danger"}
            />
            <StatCard
              title="Pending Inbound Referrals"
              value={pendingIncomingCount}
              subtitle="Requires destination clinical triage"
              icon="⏳"
              variant={pendingIncomingCount > 0 ? "warning" : "default"}
            />
            <StatCard
              title="Ambulances En Route"
              value={inTransitCount}
              subtitle="Active emergency transit"
              icon="🚑"
              variant="primary"
            />
          </div>

          {/* Quick Inbound Triage Queue */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5">
            <div className="mb-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white">
                  Active Clinical Inbound Queue
                </h3>
                <p className="text-xs text-slate-400">
                  Referrals transferred to this hospital awaiting admission or arrival confirmation
                </p>
              </div>
              <button
                onClick={() => {
                  setReferralScope("incoming");
                  setActiveTab("referrals");
                }}
                className="text-xs font-semibold text-blue-400 hover:text-blue-300 transition"
              >
                View Full Roster →
              </button>
            </div>

            <DataTable
              columns={referralColumns}
              data={inboundReferrals.filter((r) => r.status === "PENDING")}
              keyExtractor={(r) => r.referral_id}
              loading={referralLoading}
              emptyTitle="Inbound Queue Clear"
              emptyDescription="No incoming transfer requests currently awaiting review."
              pageSize={5}
            />
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* TAB 2: REFERRALS COMMAND */}
      {/* ============================================================ */}
      {activeTab === "referrals" && (
        <div className="space-y-6">
          {/* Scope Selector Tabs */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              {(["incoming", "outgoing", "all"] as const).map((scope) => (
                <button
                  key={scope}
                  onClick={() => setReferralScope(scope)}
                  className={`rounded-xl px-4 py-2 text-xs font-bold uppercase tracking-wider transition ${
                    referralScope === scope
                      ? "bg-blue-600 text-white shadow-sm"
                      : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200"
                  }`}
                >
                  {scope === "incoming"
                    ? `Inbound Requests (${inboundReferrals.length})`
                    : scope === "outgoing"
                    ? `Outbound Referrals (${outboundReferrals.length})`
                    : `All Hospital Cases (${allReferrals.length})`}
                </button>
              ))}
            </div>

            <p className="text-xs text-slate-400">
              Showing <span className="font-bold text-slate-200">{displayedReferrals.length}</span> total cases
            </p>
          </div>

          {/* Full Referrals Table */}
          <DataTable
            columns={referralColumns}
            data={displayedReferrals}
            keyExtractor={(r) => r.referral_id}
            loading={referralLoading}
            searchPlaceholder="Search Case ID, Patient ID, or Hospital..."
            searchFilterKeys={["referral_id", "patient_id", "from_hospital_id", "to_hospital_id", "reason"]}
            statusFilterKey="status"
            statusFilterOptions={[
              { label: "Pending Review", value: "PENDING" },
              { label: "Accepted & Reserved", value: "ACCEPTED" },
              { label: "In Transit", value: "IN_TRANSIT" },
              { label: "Patient Arrived", value: "ARRIVED" },
              { label: "Treatment Active", value: "TREATMENT_ACTIVE" },
              { label: "Completed", value: "COMPLETED" },
              { label: "Rejected", value: "REJECTED" },
            ]}
            emptyTitle="No Referrals Found"
            emptyDescription="There are no hospital transfer records matching the selected scope or filter."
            pageSize={10}
          />
        </div>
      )}

      {/* ============================================================ */}
      {/* TAB 3: BED INVENTORY */}
      {/* ============================================================ */}
      {activeTab === "inventory" && (
        <div className="space-y-6">
          {inventoryError && (
            <ErrorState title="Bed Inventory Alert" message={inventoryError} onRetry={loadInventory} />
          )}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-base font-bold text-white">
                  Real-Time Bed Availability & Allocation Matrix
                </h3>
                <p className="text-xs text-slate-400">
                  Authoritative operational telemetry backed by PostgreSQL transactional locks
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={openCapacityModal}
                  className="rounded-xl border border-blue-500/30 bg-blue-600/20 px-3 py-1.5 text-xs font-semibold text-blue-300 hover:bg-blue-600/30 transition flex items-center gap-1.5"
                >
                  <span>⚙️</span> Update Capacity & Resources
                </button>
                <button
                  onClick={loadInventory}
                  disabled={inventoryLoading}
                  className="rounded-xl border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition"
                >
                  {inventoryLoading ? "Refreshing..." : "Refresh Inventory"}
                </button>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-3">
              {/* General Ward Capacity */}
              <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-white">General Inpatient Ward</span>
                  <span className="rounded-full bg-blue-500/10 px-2.5 py-0.5 text-xs font-semibold text-blue-400 border border-blue-500/20">
                    Standard Care
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-2">
                  <div className="rounded-lg bg-slate-900 p-2.5 text-center">
                    <p className="text-[10px] text-slate-400 uppercase">Available</p>
                    <p className="mt-1 text-xl font-bold text-emerald-400">
                      {inventory?.available_beds ?? 0}
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-900 p-2.5 text-center">
                    <p className="text-[10px] text-slate-400 uppercase">Reserved</p>
                    <p className="mt-1 text-xl font-bold text-amber-400">
                      {inventory?.reserved_beds ?? 0}
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-900 p-2.5 text-center">
                    <p className="text-[10px] text-slate-400 uppercase">Total</p>
                    <p className="mt-1 text-xl font-bold text-slate-200">
                      {inventory?.total_general_beds ?? inventory?.total_beds ?? 0}
                    </p>
                  </div>
                </div>

                <p className="text-[11px] text-slate-400 leading-relaxed">
                  General inpatient capacity for non-critical admissions.
                </p>
              </div>

              {/* ICU Ward Capacity */}
              <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-white">Intensive Care Unit (ICU)</span>
                  <span className="rounded-full bg-rose-500/10 px-2.5 py-0.5 text-xs font-semibold text-rose-400 border border-rose-500/20">
                    Critical Care
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-2">
                  <div className="rounded-lg bg-slate-900 p-2.5 text-center">
                    <p className="text-[10px] text-slate-400 uppercase">Available</p>
                    <p className="mt-1 text-xl font-bold text-emerald-400">
                      {inventory?.available_icu_beds ?? 0}
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-900 p-2.5 text-center">
                    <p className="text-[10px] text-slate-400 uppercase">Reserved</p>
                    <p className="mt-1 text-xl font-bold text-amber-400">
                      {inventory?.reserved_icu_beds ?? 0}
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-900 p-2.5 text-center">
                    <p className="text-[10px] text-slate-400 uppercase">Total</p>
                    <p className="mt-1 text-xl font-bold text-slate-200">
                      {inventory?.total_icu_beds ?? 0}
                    </p>
                  </div>
                </div>

                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Zero double-booking guarantee: ICU beds reserved via row-level transactional locks.
                </p>
              </div>

              {/* Emergency Ward Capacity */}
              <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-white">Emergency & Trauma</span>
                  <span className="rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-semibold text-amber-400 border border-amber-500/20">
                    Immediate
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-2">
                  <div className="rounded-lg bg-slate-900 p-2.5 text-center">
                    <p className="text-[10px] text-slate-400 uppercase">Available</p>
                    <p className="mt-1 text-xl font-bold text-emerald-400">
                      {inventory?.available_emergency_beds ?? 0}
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-900 p-2.5 text-center">
                    <p className="text-[10px] text-slate-400 uppercase">Reserved</p>
                    <p className="mt-1 text-xl font-bold text-amber-400">
                      {inventory?.reserved_emergency_beds ?? 0}
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-900 p-2.5 text-center">
                    <p className="text-[10px] text-slate-400 uppercase">Total</p>
                    <p className="mt-1 text-xl font-bold text-slate-200">
                      {inventory?.total_emergency_beds ?? 0}
                    </p>
                  </div>
                </div>

                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Dedicated triage and resuscitation bays for acute emergency transfers.
                </p>
              </div>
            </div>

            {/* Facility & Equipment Readiness */}
            <div className="mt-6 rounded-xl border border-slate-800 bg-slate-950 p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <span className="text-sm font-bold text-white">Critical Support Equipment & Readiness</span>
                <span className="text-xs text-slate-400">Updated in PostgreSQL</span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                <div className="rounded-lg bg-slate-900 p-3 text-center">
                  <p className="text-[11px] text-slate-400">Oxygen Support</p>
                  <p className={`mt-1 font-bold text-xs uppercase ${inventory?.oxygen_support === "Yes" ? "text-emerald-400" : "text-rose-400"}`}>
                    {inventory?.oxygen_support === "Yes" ? "● Active" : "○ Inactive"}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-900 p-3 text-center">
                  <p className="text-[11px] text-slate-400">Ventilators</p>
                  <p className={`mt-1 font-bold text-xs uppercase ${inventory?.ventilator === "Yes" ? "text-emerald-400" : "text-rose-400"}`}>
                    {inventory?.ventilator === "Yes" ? "● Available" : "○ None"}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-900 p-3 text-center">
                  <p className="text-[11px] text-slate-400">Ambulance</p>
                  <p className={`mt-1 font-bold text-xs uppercase ${inventory?.ambulance === "Yes" ? "text-emerald-400" : "text-rose-400"}`}>
                    {inventory?.ambulance === "Yes" ? "● On Call" : "○ None"}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-900 p-3 text-center">
                  <p className="text-[11px] text-slate-400">Blood Bank</p>
                  <p className={`mt-1 font-bold text-xs uppercase ${inventory?.blood_bank === "Yes" ? "text-emerald-400" : "text-rose-400"}`}>
                    {inventory?.blood_bank === "Yes" ? "● Stocked" : "○ None"}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-900 p-3 text-center">
                  <p className="text-[11px] text-slate-400">24x7 Emergency</p>
                  <p className={`mt-1 font-bold text-xs uppercase ${inventory?.emergency_24x7 === "Yes" ? "text-emerald-400" : "text-rose-400"}`}>
                    {inventory?.emergency_24x7 === "Yes" ? "● Operational" : "○ Closed"}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* TAB 4: ADMITTED PATIENTS */}
      {/* ============================================================ */}
      {activeTab === "patients" && (
        <div className="space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h3 className="text-base font-bold text-white">Hospital Inpatient Registry</h3>
              <p className="text-xs text-slate-400">
                Patients admitted under local care available for clinical management and AI network transfer
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={openIntakeModal}
                className="flex items-center gap-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white px-3.5 py-1.5 text-xs font-bold shadow-md shadow-blue-600/25 transition active:scale-95"
              >
                <span>+</span>
                <span>Register New Patient</span>
              </button>
              <button
                onClick={loadPatients}
                disabled={patientLoading}
                className="rounded-xl border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-700 transition"
              >
                {patientLoading ? "Refreshing..." : "Refresh"}
              </button>
            </div>
          </div>

          {patientError && (
            <ErrorState title="Patient Directory Notice" message={patientError} onRetry={loadPatients} />
          )}

          <DataTable
            columns={patientColumns}
            data={patients}
            keyExtractor={(p) => p.patient_id}
            loading={patientLoading}
            searchPlaceholder="Search Patient ID, Name, or Disease..."
            searchFilterKeys={["patient_id", "name", "disease"]}
            emptyTitle="No Patients Found"
            emptyDescription="No inpatient records currently registered in this hospital's active admission database."
            pageSize={8}
          />
        </div>
      )}

      {/* ============================================================ */}
      {/* MODAL: DISPATCH AMBULANCE */}
      {/* ============================================================ */}
      <ConfirmationModal
        isOpen={Boolean(dispatchModalReferral)}
        onClose={() => setDispatchModalReferral(null)}
        onConfirm={confirmDispatch}
        title="Dispatch Emergency Transport Ambulance"
        description={`Initiate ambulance transfer for Case ${dispatchModalReferral?.referral_id}. Sets status to IN_TRANSIT.`}
        confirmLabel="Confirm & Dispatch Ambulance"
        variant="primary"
        loading={statusLoading}
      >
        <div className="space-y-3.5">
          <div>
            <label className="block text-xs font-semibold text-slate-300">
              Assigned Ambulance Vehicle ID
            </label>
            <input
              type="text"
              value={dispatchAmbulanceId}
              onChange={(e) => setDispatchAmbulanceId(e.target.value)}
              placeholder="e.g. AMB-108-ADVANCED"
              className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300">
              Estimated Transit Duration (Minutes)
            </label>
            <input
              type="number"
              min={1}
              value={dispatchEtaMinutes}
              onChange={(e) => setDispatchEtaMinutes(Number(e.target.value))}
              className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300">
              Paramedic / En-Route Clinical Notes
            </label>
            <textarea
              rows={2}
              value={dispatchNotes}
              onChange={(e) => setDispatchNotes(e.target.value)}
              placeholder="Oxygen supported, vitals stable, IV line active..."
              className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
            />
          </div>
        </div>
      </ConfirmationModal>

      {/* ============================================================ */}
      {/* MODAL: REJECT REFERRAL */}
      {/* ============================================================ */}
      <ConfirmationModal
        isOpen={Boolean(rejectModalReferral)}
        onClose={() => setRejectModalReferral(null)}
        onConfirm={confirmReject}
        title="Decline Inbound Patient Referral"
        description={`Specify clinical justification for declining Case ${rejectModalReferral?.referral_id}.`}
        confirmLabel="Decline Referral"
        variant="danger"
        loading={statusLoading}
      >
        <div>
          <label className="block text-xs font-semibold text-slate-300">
            Rejection Clinical Reason / Capacity Constraint *
          </label>
          <textarea
            rows={3}
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="e.g. No ventilator beds available; emergency surgery at capacity; redirect to regional tertiary center."
            className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-rose-500"
          />
        </div>
      </ConfirmationModal>

      {/* ============================================================ */}
      {/* MODAL: REFERRAL TIMELINE VIEW */}
      {/* ============================================================ */}
      {selectedReferralForTimeline && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-base font-bold text-white">
                Detailed Referral Audit Trail
              </h3>
              <button
                onClick={() => setSelectedReferralForTimeline(null)}
                className="rounded-lg p-1 text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>
            <div className="mt-4">
              <ReferralTimeline referral={selectedReferralForTimeline} />
            </div>
            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setSelectedReferralForTimeline(null)}
                className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700"
              >
                Close Audit View
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* MODAL: NEW PATIENT INTAKE & ADMISSION */}
      {/* ============================================================ */}
      {intakeModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-3xl max-h-[92vh] overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-5">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-blue-500/20 px-2.5 py-0.5 text-[11px] font-bold text-blue-400 border border-blue-500/30 uppercase tracking-wide">
                    Hospital Clinical Command
                  </span>
                  <span className="text-xs text-slate-400 font-mono">Facility: {hospitalId}</span>
                </div>
                <h3 className="text-lg font-bold text-white mt-1">
                  New Inpatient Intake & Bed Allocation
                </h3>
                <p className="text-xs text-slate-400">
                  Register demographics, baseline clinical vitals, and admission ward for local care and network referral eligibility.
                </p>
              </div>
              <button
                onClick={() => setIntakeModalOpen(false)}
                className="rounded-lg p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 transition"
              >
                ✕
              </button>
            </div>

            {intakeSuccessNotice && (
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-300 flex items-center gap-2">
                <span>✓</span>
                <span className="font-semibold">{intakeSuccessNotice}</span>
              </div>
            )}

            {intakeError && (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300 flex items-center gap-2">
                <span>⚠️</span>
                <span>{intakeError}</span>
              </div>
            )}

            <form onSubmit={submitPatientIntake} className="space-y-5">
              {/* SECTION 1: DEMOGRAPHICS */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 border-b border-slate-800/80 pb-1 flex items-center gap-2">
                  <span>👤</span>
                  <span>1. Patient Demographics</span>
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="sm:col-span-2">
                    <label className="block text-xs font-semibold text-slate-300">
                      Full Legal Name *
                    </label>
                    <input
                      type="text"
                      required
                      value={intakeName}
                      onChange={(e) => setIntakeName(e.target.value)}
                      placeholder="e.g. Ramesh Kumar"
                      className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300">
                      Age (Years) *
                    </label>
                    <input
                      type="number"
                      required
                      min={0}
                      max={130}
                      value={intakeAge}
                      onChange={(e) => setIntakeAge(e.target.value === "" ? "" : Number(e.target.value))}
                      placeholder="e.g. 54"
                      className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300">
                      Gender *
                    </label>
                    <select
                      value={intakeGender}
                      onChange={(e) => setIntakeGender(e.target.value)}
                      className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                    >
                      <option value="Male">Male</option>
                      <option value="Female">Female</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300">
                      Blood Group
                    </label>
                    <select
                      value={intakeBloodGroup}
                      onChange={(e) => setIntakeBloodGroup(e.target.value)}
                      className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                    >
                      <option value="A+">A+</option>
                      <option value="A-">A-</option>
                      <option value="B+">B+</option>
                      <option value="B-">B-</option>
                      <option value="AB+">AB+</option>
                      <option value="AB-">AB-</option>
                      <option value="O+">O+</option>
                      <option value="O-">O-</option>
                      <option value="Unknown">Unknown</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300">
                      Contact Phone
                    </label>
                    <input
                      type="tel"
                      value={intakePhone}
                      onChange={(e) => setIntakePhone(e.target.value)}
                      placeholder="+91-9876543210"
                      className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <label className="block text-xs font-semibold text-slate-300">
                      Emergency Contact / Guardian
                    </label>
                    <input
                      type="text"
                      value={intakeEmergencyContact}
                      onChange={(e) => setIntakeEmergencyContact(e.target.value)}
                      placeholder="e.g. Sunita Devi (Spouse) - 9876543211"
                      className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300">
                      District & State
                    </label>
                    <input
                      type="text"
                      value={`${intakeDistrict}, ${intakeState}`}
                      disabled
                      className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-xs text-slate-400 outline-none cursor-not-allowed"
                    />
                  </div>
                </div>
              </div>

              {/* SECTION 2: CLINICAL ADMISSION & BED ALLOCATION */}
              <div className="space-y-3 pt-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 border-b border-slate-800/80 pb-1 flex items-center gap-2">
                  <span>🩺</span>
                  <span>2. Clinical Diagnosis & Bed Allocation</span>
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="sm:col-span-3">
                    <label className="block text-xs font-semibold text-slate-300">
                      Chief Complaint / Primary Diagnosis *
                    </label>
                    <input
                      type="text"
                      required
                      value={intakeChiefComplaint}
                      onChange={(e) => setIntakeChiefComplaint(e.target.value)}
                      placeholder="e.g. Acute Coronary Syndrome, STEMI anterior wall"
                      className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300">
                      Required Specialty *
                    </label>
                    <select
                      value={intakeSpecialty}
                      onChange={(e) => setIntakeSpecialty(e.target.value)}
                      className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                    >
                      <option value="Cardiology">Cardiology</option>
                      <option value="Neurology">Neurology</option>
                      <option value="Trauma/Emergency">Trauma & Emergency</option>
                      <option value="General Medicine">General Medicine</option>
                      <option value="Orthopedics">Orthopedics</option>
                      <option value="Pediatrics">Pediatrics</option>
                      <option value="Pulmonology">Pulmonology</option>
                      <option value="Critical Care">Critical Care / ICU</option>
                      <option value="Nephrology">Nephrology / Dialysis</option>
                      <option value="General Surgery">General Surgery</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300">
                      Assigned Bed Category *
                    </label>
                    <select
                      value={intakeBedType}
                      onChange={(e) => setIntakeBedType(e.target.value as any)}
                      className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500 font-semibold"
                    >
                      <option value="GENERAL">General Inpatient Bed</option>
                      <option value="ICU">Intensive Care Unit (ICU)</option>
                      <option value="VENTILATOR">ICU Ventilator Bed</option>
                      <option value="OXYGEN">Oxygen Supported Bay</option>
                      <option value="EMERGENCY_BAY">Emergency Triage Bay</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300">
                      Triage Severity Level *
                    </label>
                    <select
                      value={intakeSeverity}
                      onChange={(e) => setIntakeSeverity(e.target.value as any)}
                      className={`mt-1 w-full rounded-xl border px-3 py-2 text-xs font-bold outline-none focus:border-blue-500 ${
                        intakeSeverity === "CRITICAL"
                          ? "border-rose-500/50 bg-rose-950/30 text-rose-400"
                          : intakeSeverity === "HIGH"
                          ? "border-amber-500/50 bg-amber-950/30 text-amber-400"
                          : "border-slate-700 bg-slate-950 text-emerald-400"
                      }`}
                    >
                      <option value="CRITICAL">CRITICAL (Immediate Care)</option>
                      <option value="HIGH">HIGH (Urgent Attention)</option>
                      <option value="MODERATE">MODERATE (Standard Inpatient)</option>
                      <option value="LOW">LOW (Mild / Observation)</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* SECTION 3: BASELINE VITALS */}
              <div className="space-y-3 pt-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 border-b border-slate-800/80 pb-1 flex items-center gap-2">
                  <span>💓</span>
                  <span>3. Baseline Clinical Vitals</span>
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-6 gap-2.5">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400">
                      SpO2 (%)
                    </label>
                    <input
                      type="number"
                      min={40}
                      max={100}
                      value={intakeSpO2}
                      onChange={(e) => setIntakeSpO2(e.target.value === "" ? "" : Number(e.target.value))}
                      placeholder="e.g. 96"
                      className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-white outline-none focus:border-blue-500 font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400">
                      Heart Rate (bpm)
                    </label>
                    <input
                      type="number"
                      min={30}
                      max={250}
                      value={intakeHeartRate}
                      onChange={(e) => setIntakeHeartRate(e.target.value === "" ? "" : Number(e.target.value))}
                      placeholder="e.g. 84"
                      className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-white outline-none focus:border-blue-500 font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400">
                      Systolic BP
                    </label>
                    <input
                      type="number"
                      min={50}
                      max={260}
                      value={intakeSystolicBP}
                      onChange={(e) => setIntakeSystolicBP(e.target.value === "" ? "" : Number(e.target.value))}
                      placeholder="120"
                      className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-white outline-none focus:border-blue-500 font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400">
                      Diastolic BP
                    </label>
                    <input
                      type="number"
                      min={30}
                      max={180}
                      value={intakeDiastolicBP}
                      onChange={(e) => setIntakeDiastolicBP(e.target.value === "" ? "" : Number(e.target.value))}
                      placeholder="80"
                      className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-white outline-none focus:border-blue-500 font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400">
                      Temp (°F)
                    </label>
                    <input
                      type="number"
                      step={0.1}
                      min={85}
                      max={112}
                      value={intakeTemp}
                      onChange={(e) => setIntakeTemp(e.target.value === "" ? "" : Number(e.target.value))}
                      placeholder="98.6"
                      className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-white outline-none focus:border-blue-500 font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400">
                      Resp Rate (/min)
                    </label>
                    <input
                      type="number"
                      min={6}
                      max={70}
                      value={intakeRespRate}
                      onChange={(e) => setIntakeRespRate(e.target.value === "" ? "" : Number(e.target.value))}
                      placeholder="18"
                      className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-white outline-none focus:border-blue-500 font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* SECTION 4: CLINICAL NOTES */}
              <div className="space-y-1.5 pt-2">
                <label className="block text-xs font-semibold text-slate-300">
                  Initial Clinical Admission Notes
                </label>
                <textarea
                  rows={2}
                  value={intakeNotes}
                  onChange={(e) => setIntakeNotes(e.target.value)}
                  placeholder="Record initial findings, pre-existing comorbidities, medication orders..."
                  className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                />
              </div>

              {/* Form Actions */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIntakeModalOpen(false)}
                  disabled={intakeLoading}
                  className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-700 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={intakeLoading}
                  className="flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2 text-xs font-bold text-white hover:bg-blue-500 shadow-lg shadow-blue-600/25 transition disabled:opacity-50"
                >
                  {intakeLoading && (
                    <span className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  )}
                  <span>{intakeLoading ? "Saving Patient..." : "Complete Admission"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 2-STEP CLINICAL REFERRAL MODAL (CDS + AI RECOMMENDATIONS) */}
      {/* ============================================================ */}
      {referralModalPatient && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-3xl max-h-[92vh] overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-5">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-blue-500/20 px-2 py-0.5 text-[10px] font-bold text-blue-400 border border-blue-500/30">
                    Network Referral Command
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    Patient ID: {referralModalPatient.patient_id}
                  </span>
                </div>
                <h3 className="text-lg font-bold text-white mt-1">
                  Inter-Hospital Clinical Referral Workflow
                </h3>
                <p className="text-xs text-slate-400">
                  Patient: <span className="text-white font-semibold">{referralModalPatient.name}</span> • {referralModalPatient.age}y {referralModalPatient.gender}
                </p>
              </div>
              <button
                onClick={() => setReferralModalPatient(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 transition"
              >
                ✕
              </button>
            </div>

            {/* Stepper Header */}
            <div className="grid grid-cols-2 gap-2 text-center text-xs font-semibold">
              <div
                className={`rounded-xl py-2 px-3 border transition ${
                  referralModalStep === 1
                    ? "border-blue-500 bg-blue-500/10 text-blue-300 font-bold shadow-inner"
                    : "border-slate-800 bg-slate-950/60 text-slate-400"
                }`}
              >
                <span>Step 1: Current Condition Assessment</span>
              </div>
              <div
                className={`rounded-xl py-2 px-3 border transition ${
                  referralModalStep === 2
                    ? "border-blue-500 bg-blue-500/10 text-blue-300 font-bold shadow-inner"
                    : "border-slate-800 bg-slate-950/60 text-slate-400"
                }`}
              >
                <span>Step 2: AI-Ranked Suitable Facilities</span>
              </div>
            </div>

            {/* STEP 1: CURRENT CLINICAL CONDITION ASSESSMENT */}
            {referralModalStep === 1 && (
              <div className="space-y-4">
                <div className="rounded-xl border border-blue-500/30 bg-blue-500/10 p-3 text-xs text-blue-200 flex items-start gap-2.5">
                  <span className="text-base">ℹ️</span>
                  <div>
                    <span className="font-bold">Clinical Condition Evaluation: </span>
                    Provide the patient's updated real-time physiological condition, required specialized destination capability, and transport urgency. The AI recommendation engine scores facilities against these parameters.
                  </div>
                </div>

                {recError && (
                  <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
                    ⚠️ {recError}
                  </div>
                )}

                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300">
                      Current Clinical Condition / Reason for Referral *
                    </label>
                    <textarea
                      rows={2}
                      value={evalConditionSummary}
                      onChange={(e) => setEvalConditionSummary(e.target.value)}
                      placeholder="e.g. Deteriorating SpO2 to 86%, acute respiratory distress, primary PCI / Cath Lab required immediately..."
                      className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-slate-300">
                        Urgency / Triage Level *
                      </label>
                      <select
                        value={evalUrgency}
                        onChange={(e) => setEvalUrgency(e.target.value as any)}
                        className={`mt-1 w-full rounded-xl border px-3 py-2 text-xs font-bold outline-none ${
                          evalUrgency === "CRITICAL"
                            ? "border-rose-500/50 bg-rose-950/30 text-rose-400"
                            : evalUrgency === "URGENT" || evalUrgency === "EMERGENCY"
                            ? "border-amber-500/50 bg-amber-950/30 text-amber-400"
                            : "border-slate-700 bg-slate-950 text-emerald-400"
                        }`}
                      >
                        <option value="CRITICAL">CRITICAL (Immediate Transfer)</option>
                        <option value="EMERGENCY">EMERGENCY (&lt; 1 Hour)</option>
                        <option value="URGENT">URGENT (&lt; 3 Hours)</option>
                        <option value="ROUTINE">ROUTINE (Elective Transfer)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-300">
                        Required Specialty *
                      </label>
                      <select
                        value={evalSpecialty}
                        onChange={(e) => setEvalSpecialty(e.target.value)}
                        className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                      >
                        <option value="Cardiology">Cardiology</option>
                        <option value="Neurology">Neurology</option>
                        <option value="Trauma/Emergency">Trauma / Emergency Care</option>
                        <option value="Pulmonology">Pulmonology</option>
                        <option value="Critical Care">Critical Care / ICU</option>
                        <option value="Nephrology">Nephrology</option>
                        <option value="Orthopedics">Orthopedics</option>
                        <option value="General Surgery">General Surgery</option>
                        <option value="General Medicine">General Medicine</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-300">
                        Required Destination Bed *
                      </label>
                      <select
                        value={evalBedType}
                        onChange={(e) => setEvalBedType(e.target.value as any)}
                        className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500 font-semibold"
                      >
                        <option value="ICU">Intensive Care Unit (ICU)</option>
                        <option value="VENTILATOR">ICU Ventilator Bed</option>
                        <option value="GENERAL">General Inpatient Bed</option>
                        <option value="EMERGENCY">Emergency / Bay</option>
                        <option value="NICU">Neonatal ICU (NICU)</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300">
                      Transport / Transit Requirement *
                    </label>
                    <select
                      value={evalTransport}
                      onChange={(e) => setEvalTransport(e.target.value as any)}
                      className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                    >
                      <option value="ALS_AMBULANCE">Advanced Life Support (ALS) Ambulance (Ventilator / Paramedic)</option>
                      <option value="BASIC_AMBULANCE">Basic Ambulance (BLS with Oxygen)</option>
                      <option value="NONE">Standard / Patient Self-Transport</option>
                    </select>
                  </div>

                  {/* Updated Vitals inputs */}
                  <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 space-y-2">
                    <p className="text-[11px] font-bold text-slate-300 uppercase tracking-wide">
                      Updated Live Physiological Vitals
                    </p>
                    <div className="grid grid-cols-2 sm:grid-cols-6 gap-2">
                      <div>
                        <label className="block text-[10px] text-slate-400">SpO2 (%)</label>
                        <input
                          type="number"
                          value={evalSpO2}
                          onChange={(e) => setEvalSpO2(e.target.value === "" ? "" : Number(e.target.value))}
                          placeholder="e.g. 91"
                          className="mt-0.5 w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-white font-mono"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] text-slate-400">Heart Rate</label>
                        <input
                          type="number"
                          value={evalHeartRate}
                          onChange={(e) => setEvalHeartRate(e.target.value === "" ? "" : Number(e.target.value))}
                          placeholder="e.g. 110"
                          className="mt-0.5 w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-white font-mono"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] text-slate-400">Systolic BP</label>
                        <input
                          type="number"
                          value={evalSystolicBP}
                          onChange={(e) => setEvalSystolicBP(e.target.value === "" ? "" : Number(e.target.value))}
                          placeholder="150"
                          className="mt-0.5 w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-white font-mono"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] text-slate-400">Diastolic BP</label>
                        <input
                          type="number"
                          value={evalDiastolicBP}
                          onChange={(e) => setEvalDiastolicBP(e.target.value === "" ? "" : Number(e.target.value))}
                          placeholder="95"
                          className="mt-0.5 w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-white font-mono"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] text-slate-400">Temp (°F)</label>
                        <input
                          type="number"
                          step={0.1}
                          value={evalTemp}
                          onChange={(e) => setEvalTemp(e.target.value === "" ? "" : Number(e.target.value))}
                          placeholder="99.2"
                          className="mt-0.5 w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-white font-mono"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] text-slate-400">GCS Score</label>
                        <input
                          type="number"
                          min={3}
                          max={15}
                          value={evalGCS}
                          onChange={(e) => setEvalGCS(e.target.value === "" ? "" : Number(e.target.value))}
                          placeholder="14"
                          className="mt-0.5 w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-white font-mono"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                  <button
                    type="button"
                    onClick={() => setReferralModalPatient(null)}
                    className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-700 transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleRunConditionAssessment}
                    disabled={recLoading || !evalConditionSummary.trim()}
                    className="flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2 text-xs font-bold text-white hover:bg-blue-500 shadow-lg shadow-blue-600/25 transition disabled:opacity-50"
                  >
                    {recLoading && (
                      <span className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    )}
                    <span>{recLoading ? "Scoring Facilities..." : "Find Suitable Hospitals →"}</span>
                  </button>
                </div>
              </div>
            )}

            {/* STEP 2: AI-RANKED SUITABLE DESTINATION HOSPITALS */}
            {referralModalStep === 2 && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setReferralModalStep(1)}
                      className="text-xs text-blue-400 hover:text-blue-300 font-semibold flex items-center gap-1"
                    >
                      <span>←</span>
                      <span>Modify Assessment</span>
                    </button>
                    <span className="text-slate-600">•</span>
                    <span className="text-xs text-slate-300">
                      Criteria: <strong className="text-white">{evalSpecialty}</strong> ({evalBedType}) • <span className="font-bold text-amber-400">{evalUrgency}</span>
                    </span>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">
                    {recommendations.length} Destination(s) Ranked
                  </span>
                </div>

                {createReferralError && (
                  <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
                    ⚠️ {createReferralError}
                  </div>
                )}

                {createReferralSuccess && (
                  <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-300">
                    ✓ {createReferralSuccess}
                  </div>
                )}

                {/* Recommendations list */}
                <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
                  {recommendations.length > 0 ? (
                    recommendations.map((h, i) => {
                      const isSelected = referralTargetHospitalId === h.hospital_id;
                      return (
                        <div
                          key={h.hospital_id || i}
                          onClick={() => setReferralTargetHospitalId(h.hospital_id)}
                          className={`cursor-pointer rounded-xl border p-3.5 transition ${
                            isSelected
                              ? "border-blue-500 bg-blue-950/40 ring-2 ring-blue-500/80 shadow-lg"
                              : "border-slate-800 bg-slate-950 hover:border-slate-700 hover:bg-slate-900/60"
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex items-center gap-2.5">
                              <span className="rounded-full bg-blue-500/20 px-2 py-0.5 text-[11px] font-bold text-blue-400">
                                #{i + 1}
                              </span>
                              <div>
                                <span className="text-xs font-bold text-white block">
                                  {h.hospital_name || h.name || h.hospital_id}
                                </span>
                                <span className="text-[10px] text-slate-400">
                                  Facility ID: <span className="font-mono">{h.hospital_id}</span> • {h.district}, {h.state}
                                </span>
                              </div>
                            </div>

                            <div className="flex items-center gap-2">
                              <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs font-bold text-emerald-400 border border-emerald-500/20">
                                {h.match_score ? `${h.match_score}% Match` : formatModelFitScore(h.success_probability)}
                              </span>
                              <div className={`h-4 w-4 rounded-full border flex items-center justify-center ${
                                isSelected ? "border-blue-500 bg-blue-600" : "border-slate-700"
                              }`}>
                                {isSelected && <span className="h-1.5 w-1.5 rounded-full bg-white" />}
                              </div>
                            </div>
                          </div>

                          {/* Quick indicators */}
                          <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px] text-slate-300 border-t border-slate-800/80 pt-2">
                            <span className="flex items-center gap-1 text-slate-400">
                              <span>📍</span>
                              <span>{formatDistance(h.distance_km)} (~{h.eta_minutes || 25} min transit)</span>
                            </span>
                            <span className="flex items-center gap-1 text-emerald-400 font-semibold">
                              <span>🛏️</span>
                              <span>{h.available_icu_beds} ICU Beds</span>
                            </span>
                            <span className="flex items-center gap-1 text-slate-300">
                              <span>🏥</span>
                              <span>{h.available_beds} General Beds</span>
                            </span>
                            {h.ventilators === "Yes" && (
                              <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-cyan-300 font-medium">
                                ⚡ Ventilator Ready
                              </span>
                            )}
                          </div>

                          {/* Rationale */}
                          {h.ai_rationale && h.ai_rationale.length > 0 && (
                            <div className="mt-2 space-y-0.5 text-[11px] text-slate-400 bg-slate-900/60 rounded-lg p-2 border border-slate-800/60">
                              {h.ai_rationale.map((r, ri) => (
                                <p key={ri} className="flex items-start gap-1.5">
                                  <span className="text-emerald-400 shrink-0">✓</span>
                                  <span>{r}</span>
                                </p>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })
                  ) : (
                    <div className="text-center py-8 text-xs text-slate-500">
                      No eligible destination facilities found. Please check condition assessment.
                    </div>
                  )}
                </div>

                {/* Selected Hospital Confirmation & Trigger */}
                <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 flex flex-col sm:flex-row items-center justify-between gap-3">
                  <div>
                    <p className="text-[11px] text-slate-400">Selected Destination Facility:</p>
                    <p className="text-xs font-bold text-white">
                      {referralTargetHospitalId ? (
                        <>
                          <span className="text-blue-400 font-mono">{referralTargetHospitalId}</span> (
                          {recommendations.find((r) => r.hospital_id === referralTargetHospitalId)?.hospital_name || "Network Hospital"}
                          )
                        </>
                      ) : (
                        <span className="text-amber-400">Select a hospital above</span>
                      )}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setReferralModalStep(1)}
                      className="rounded-xl border border-slate-700 bg-slate-800 px-3.5 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-700 transition"
                    >
                      ← Back
                    </button>
                    <button
                      type="button"
                      onClick={submitCreateReferral}
                      disabled={createReferralLoading || !referralTargetHospitalId.trim()}
                      className="flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2 text-xs font-bold text-white hover:bg-blue-500 shadow-lg shadow-blue-600/25 transition disabled:opacity-50"
                    >
                      {createReferralLoading && (
                        <span className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                      )}
                      <span>{createReferralLoading ? "Dispatching Referral..." : "Initiate Referral →"}</span>
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* DRAWER: PATIENT REFERRAL HISTORY */}
      {/* ============================================================ */}
      {selectedPatientForHistory && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/75 backdrop-blur-sm animate-fade-in">
          <div className="h-full w-full max-w-xl overflow-y-auto border-l border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white">
                  Patient Network Referral History
                </h3>
                <p className="text-xs text-slate-400">
                  {selectedPatientForHistory.name} ({selectedPatientForHistory.patient_id})
                </p>
              </div>
              <button
                onClick={() => setSelectedPatientForHistory(null)}
                className="rounded-lg p-1 text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            {patientReferralLoading ? (
              <LoadingState message="Fetching patient referral history..." />
            ) : patientReferrals.length === 0 ? (
              <EmptyState
                title="No Network Transfer Records"
                description="This patient has no recorded referral transfers between network facilities."
              />
            ) : (
              <div className="space-y-4">
                {patientReferrals.map((ref) => (
                  <div key={ref.referral_id} className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-blue-400">
                        {ref.referral_id}
                      </span>
                      <StatusBadge status={ref.status} size="sm" />
                    </div>
                    <div className="mt-2 text-xs text-slate-400 space-y-1">
                      <p>
                        From: <span className="text-slate-200">{ref.from_hospital_id}</span> → To:{" "}
                        <span className="text-slate-200">{ref.to_hospital_id}</span>
                      </p>
                      <p>Priority: {ref.priority} • Bed: {ref.bed_type || "ICU"}</p>
                      <p>Reason: {ref.reason}</p>
                      <p className="text-[10px] text-slate-400 pt-1">
                        Initiated: {formatDateTime(ref.created_at)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* MODAL: UPDATE BED CAPACITY & HOSPITAL RESOURCES */}
      {/* ============================================================ */}
      {capacityModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white">
                  Update Bed Capacity & Facility Resources
                </h3>
                <p className="text-xs text-slate-400">
                  Transactional update synchronized directly with PostgreSQL
                </p>
              </div>
              <button
                onClick={() => setCapacityModalOpen(false)}
                className="rounded-lg p-1 text-slate-400 hover:text-white"
                disabled={capSaving}
              >
                ✕
              </button>
            </div>

            {capModalError && (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
                {capModalError}
              </div>
            )}

            {capModalSuccess && (
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-300">
                {capModalSuccess}
              </div>
            )}

            <div className="space-y-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Bed Capacity Management
              </h4>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-[11px] font-medium text-slate-300">
                    General Ward
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={capGeneral}
                    onChange={(e) => setCapGeneral(Math.max(0, parseInt(e.target.value) || 0))}
                    className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                  />
                  <p className="mt-1 text-[10px] text-slate-400">
                    Occupied+Res: {(inventory?.occupied_beds || 0) + (inventory?.reserved_beds || 0)}
                  </p>
                </div>

                <div>
                  <label className="text-[11px] font-medium text-slate-300">
                    ICU Ward
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={capICU}
                    onChange={(e) => setCapICU(Math.max(0, parseInt(e.target.value) || 0))}
                    className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                  />
                  <p className="mt-1 text-[10px] text-slate-400">
                    Occupied+Res: {(inventory?.occupied_icu_beds || 0) + (inventory?.reserved_icu_beds || 0)}
                  </p>
                </div>

                <div>
                  <label className="text-[11px] font-medium text-slate-300">
                    Emergency Bay
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={capEmergency}
                    onChange={(e) => setCapEmergency(Math.max(0, parseInt(e.target.value) || 0))}
                    className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                  />
                  <p className="mt-1 text-[10px] text-slate-400">
                    Occupied+Res: {(inventory?.occupied_emergency_beds || 0) + (inventory?.reserved_emergency_beds || 0)}
                  </p>
                </div>
              </div>

              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 pt-2 border-t border-slate-800">
                Facility Support Resources
              </h4>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="text-[11px] text-slate-300">Oxygen Support</label>
                  <select
                    value={resOxygen}
                    onChange={(e) => setResOxygen(e.target.value)}
                    className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                  >
                    <option value="Yes">Yes (Available)</option>
                    <option value="No">No (Unavailable)</option>
                  </select>
                </div>

                <div>
                  <label className="text-[11px] text-slate-300">Ventilator Units</label>
                  <select
                    value={resVentilator}
                    onChange={(e) => setResVentilator(e.target.value)}
                    className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                  >
                    <option value="Yes">Yes (Available)</option>
                    <option value="No">No (Unavailable)</option>
                  </select>
                </div>

                <div>
                  <label className="text-[11px] text-slate-300">Ambulance Readiness</label>
                  <select
                    value={resAmbulance}
                    onChange={(e) => setResAmbulance(e.target.value)}
                    className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                  >
                    <option value="Yes">Yes (On Call)</option>
                    <option value="No">No (Unavailable)</option>
                  </select>
                </div>

                <div>
                  <label className="text-[11px] text-slate-300">Blood Bank Supply</label>
                  <select
                    value={resBloodBank}
                    onChange={(e) => setResBloodBank(e.target.value)}
                    className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                  >
                    <option value="Yes">Yes (Stocked)</option>
                    <option value="No">No (Unavailable)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-[11px] text-slate-300">24x7 Emergency Services</label>
                <select
                  value={resEmergency24x7}
                  onChange={(e) => setResEmergency24x7(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                >
                  <option value="Yes">Yes (24x7 Operational)</option>
                  <option value="No">No (Limited Hours)</option>
                </select>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setCapacityModalOpen(false)}
                disabled={capSaving}
                className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-700 transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveCapacityAndResources}
                disabled={capSaving}
                className="rounded-xl bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-500 transition disabled:opacity-50 flex items-center gap-1.5"
              >
                {capSaving ? "Saving to PostgreSQL..." : "Save Changes"}
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
