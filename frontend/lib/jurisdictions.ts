/**
 * Canonical Geographic Divisions for State & District Jurisdiction Verification
 * Replicated exactly from backend `src/services/registration_service.py`
 */

export const CANONICAL_DIVISIONS: Record<string, string[]> = {
  Bihar: [
    "Begusarai",
    "Bhagalpur",
    "Darbhanga",
    "Gaya",
    "Munger",
    "Muzaffarpur",
    "Patna",
    "Purnea",
    "Purnia",
  ],
  Delhi: [
    "East Delhi",
    "New Delhi",
    "North Delhi",
    "South Delhi",
    "West Delhi",
  ],
  Gujarat: [
    "Ahmedabad",
    "Gandhinagar",
    "Rajkot",
    "Surat",
    "Vadodara",
  ],
  Karnataka: [
    "Belagavi",
    "Bengaluru",
    "Hubballi",
    "Mangaluru",
    "Mysuru",
  ],
  Maharashtra: [
    "Aurangabad",
    "Mumbai",
    "Nagpur",
    "Nashik",
    "Pune",
    "Thane",
  ],
  Punjab: [
    "Amritsar",
    "Bathinda",
    "Hoshiarpur",
    "Jalandhar",
    "Ludhiana",
    "Mohali",
    "Patiala",
  ],
  Rajasthan: [
    "Ajmer",
    "Bikaner",
    "Jaipur",
    "Jodhpur",
    "Kota",
    "Udaipur",
  ],
  "Tamil Nadu": [
    "Chennai",
    "Coimbatore",
    "Madurai",
    "Salem",
    "Tiruchirappalli",
  ],
  "Uttar Pradesh": [
    "Agra",
    "Gorakhpur",
    "Kanpur",
    "Lucknow",
    "Meerut",
    "Noida",
    "Prayagraj",
    "Varanasi",
  ],
  "West Bengal": [
    "Asansol",
    "Durgapur",
    "Howrah",
    "Kolkata",
    "Siliguri",
  ],
  Haryana: [
    "Ambala",
    "Faridabad",
    "Gurugram",
    "Hisar",
    "Panipat",
    "Rohtak",
  ],
  Kerala: [
    "Ernakulam",
    "Kozhikode",
    "Malappuram",
    "Thiruvananthapuram",
    "Thrissur",
  ],
  "Madhya Pradesh": [
    "Bhopal",
    "Gwalior",
    "Indore",
    "Jabalpur",
    "Ujjain",
  ],
  Odisha: [
    "Bhubaneswar",
    "Cuttack",
    "Puri",
    "Rourkela",
    "Sambalpur",
  ],
  Telangana: [
    "Hyderabad",
    "Karimnagar",
    "Khammam",
    "Nizamabad",
    "Warangal",
  ],
  "Andhra Pradesh": [
    "Guntur",
    "Kurnool",
    "Nellore",
    "Tirupati",
    "Vijayawada",
    "Visakhapatnam",
  ],
};

export const CANONICAL_STATES = Object.keys(CANONICAL_DIVISIONS).sort();

export function getDistrictsForState(state: string): string[] {
  return CANONICAL_DIVISIONS[state] || [];
}

export function isValidJurisdiction(state: string, district?: string): boolean {
  if (!CANONICAL_DIVISIONS[state]) return false;
  if (district) {
    const norm = normalizeDistrictName(district);
    const stateDistricts = (CANONICAL_DIVISIONS[state] || []).map(d => normalizeDistrictName(d));
    if (!stateDistricts.includes(norm)) return false;
  }
  return true;
}

export function normalizeDistrictName(district?: string | null): string {
  if (!district) return "";
  const d = district.trim().toLowerCase();
  if (d === "purnea" || d === "purnia") return "Purnea";
  return district.trim();
}
