#!/usr/bin/env python3
"""
ETL for PriMock-57 → Braintrust SOAP dataset.

Writes data/soap_dataset.jsonl, where each line is:
{
  "input": "<speaker-tagged transcript>",
  "expected": {
      "subjective": "...",  # Patient's own words, history, and relevant context
      "objective":  "...",  # Measurable and observable data
      "assessment": "...",  # Clinician's interpretation
      "plan":       "..."   # Next steps and follow-up
  }
}

SOAP Note Structure:
- Subjective: Patient's own words, chief complaint, symptom description (onset, location, 
  quality, severity, timing, relieving/aggravating factors), review of systems, medications, 
  allergies, social/family history.
- Objective: Measurable, observable data including vital signs, physical exam findings, 
  lab/imaging results, and clinician observations.
- Assessment: Clinician's interpretation including working diagnosis, differential diagnosis, 
  comparison to baseline, and risk stratification.
- Plan: Next steps including further tests, medications, procedures, patient education, 
  follow-up timeline, and safety-net instructions.
"""

import json
import re
import pathlib
import textgrid
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

# ───────────────────────────── paths ──────────────────────────────
ROOT = pathlib.Path("data/primock57")        # cloned PriMock-57 repo
TRANS_DIR = ROOT / "transcripts"             # contains doctor/patient TextGrid files
NOTES_DIR = ROOT / "notes"                   # contains JSON files with SOAP notes
OUTFILE = pathlib.Path("data/soap_dataset.jsonl")
OUTFILE.parent.mkdir(parents=True, exist_ok=True)

# ────────────────────── placeholders for empty fields ─────────────
PLACEHOLDER = {
    "subjective":  "No subjective information available.",
    "objective":   "No objective information available.",
    "assessment":  "No assessment information available.",
    "plan":        "No plan information available.",
}

# ─────────────────────── regex utilities ──────────────────────────
TAG_RE = re.compile(r"<[^>]+>")
WS_RE  = re.compile(r"\s+")

def clean(txt: str) -> str:
    """Strip XML-ish tags and collapse whitespace."""
    return WS_RE.sub(" ", TAG_RE.sub("", txt or "")).strip()

def parse_grid(grid_path: pathlib.Path, speaker: str) -> List[Tuple[float, str]]:
    """Parse a TextGrid file and return list of (timestamp, utterance) pairs."""
    try:
        tg = textgrid.TextGrid.fromFile(str(grid_path))
        tier = tg.getFirst("Speaker")
        if tier is None:
            print(f"WARNING: No Speaker tier found in {grid_path}")
            return []
        return [(intv.minTime, f"{speaker}: {clean(intv.mark)}") for intv in tier if intv.mark.strip()]
    except Exception as e:
        print(f"ERROR: Failed to parse {grid_path}: {str(e)}")
        return []

def get_consultation_id(file_path: pathlib.Path) -> str:
    """Extract consultation ID from file path (e.g., 'day1_consultation01')."""
    return file_path.stem.replace("_doctor", "").replace("_patient", "")

# ────────────── patterns to recognise SOAP headers ────────────────
# Accepts colons, hyphens, or EN-dashes after the header token.
D = r"[:\-\u2013]"      # delimiter: colon, hyphen, EN dash
SOAP_HDR = {
    "subjective":  rf"\b(S|Subj|Subjective|PC|HPC|Hx|H/O|History|Chief Complaint|CC|PMH|DH|SH|ICE|FH){D}",
    "objective":   rf"\b(O|Obj|Objective|O/E|O\\E|Ex|Exam|Examination|Vitals|VS|Physical Exam|PE|Systemically|No |Feels |feels ){D}",
    "assessment":  rf"\b(A|Ass|Assessment|Imp|Impression|Dx|Diagnosis|Working Dx|Differential|DDx){D}",
    "plan":        rf"\b(P|Pln|Plan|Follow-up|FU|Review|Discussed|Conservative|Management|Mx|Treatment|Rx){D}",
}
SOAP_RE = {k: re.compile(pat, flags=re.I) for k, pat in SOAP_HDR.items()}

# Common symptoms and findings that indicate objective information
OBJECTIVE_PATTERNS = [
    # Vital signs and measurements
    "sore throat", "runny nose", "nasal congestion", "cough", "fever",
    "sweats", "appetite", "rash", "pain", "ache", "SOB", "breathing",
    "chest", "temp", "temperature", "pulse", "BP", "heart rate",
    "oxygen", "sats", "saturation", "burning", "constant", "gradual",
    "progressive", "headache", "visual", "palpitations", "nausea",
    "vomiting", "bowel", "urinary", "dysuria", "haematuria",
    # Physical examination findings
    "tender", "swollen", "inflamed", "red", "warm", "cool", "pale",
    "cyanotic", "jaundiced", "oedema", "edema", "mass", "lump",
    "lesion", "wound", "scar", "rash", "bruise", "swelling",
    # Measurements and observations
    "weight", "height", "BMI", "circumference", "range of motion",
    "strength", "reflexes", "sensation", "mobility", "gait",
    # System-specific findings
    "breath sounds", "heart sounds", "bowel sounds", "pulses",
    "abdomen", "chest", "heart", "lungs", "throat", "ears", "eyes",
    "nose", "mouth", "neck", "back", "extremities", "skin",
    # Common prefixes indicating findings
    "bilateral", "unilateral", "mild", "moderate", "severe",
    "decreased", "increased", "normal", "abnormal", "positive",
    "negative", "present", "absent",
    # Additional physical findings
    "periumbilical", "severity", "difficulty", "PV bleeding",
    # System review headers
    "RS:", "GI:", "Neuro:", "LS:", "SE:", "CVS:", "MSK:",
    # Examination findings
    "no lip swelling", "speaking normally", "no airways compromise",
    "no rash seen", "no joint swelling", "no neck stiffness",
    # General appearance
    "looks well", "appears well", "not in pain", "comfortable",
    "alert", "oriented", "distressed", "uncomfortable",
    # Specific findings
    "erythema", "swelling", "tenderness", "crepitus", "effusion",
    "discharge", "exudate", "lesion", "nodule", "mass"
]

# Patterns that indicate assessment information
ASSESSMENT_PATTERNS = [
    # Status indicators
    "improving", "settling", "worsening", "stable", "resolved",
    # Diagnostic qualifiers
    "likely", "possibly", "probable", "suspected", "consistent with",
    "differential", "diagnosis", "working diagnosis", "need to exclude",
    "rule out", "?", "query", "impression", "imp", "assessment",
    "appears to be", "seems to be", "looks like", "suggestive of",
    "indicative of", "compatible with", "secondary to", "due to",
    "caused by", "resulting from", "concerning for", "worried about",
    "suspicious for", "high probability of", "low probability of",
    # Additional assessment patterns
    "localized", "inflammatory", "reaction", "evidence of",
    "acute", "chronic", "exclude", "pathology", "underlying",
    "differential diagnosis", "working diagnosis", "impression",
    "assessment", "diagnosis", "likely", "possibly", "probably",
    "suspected", "consistent with", "compatible with", "suggestive of",
    "indicative of", "secondary to", "due to", "caused by",
    "resulting from", "concerning for", "worried about",
    "suspicious for", "high probability of", "low probability of",
    # Common diagnostic prefixes
    "possible", "probable", "suspected", "presumed", "provisional",
    "working", "differential", "confirmed", "established",
    # Diagnostic uncertainty
    "need to exclude", "rule out", "? ", "query", "versus",
    "differential includes", "to consider", "impression of"
]

# Patterns that indicate plan information
PLAN_PATTERNS = [
    # Action items
    "plan:", "follow up", "review in", "discussed", "conservative",
    "prescribe", "prescription", "medication", "advice", "advise",
    "recommend", "recommendation", "refer", "referral", "monitor",
    "monitoring", "safety net", "red flags", "return if", "return to",
    "follow-up", "follow up", "next steps", "action plan", "management",
    "treatment", "therapy", "investigation", "test", "scan", "imaging",
    "bloods", "blood test", "urine", "stool", "sample", "specimen",
    # Additional plan patterns
    "warned re", "red flags", "urgent medical review", "allergy testing",
    "ring back", "reassurance", "OTC", "antihistamines", "f2f appointment",
    "blood tests", "crp", "esr", "thick and thin blood films", "routine",
    "a/e", "second GP's assessment", "screening bloods", "Lyme serology",
    "GP", "regular paracetamol", "naproxen", "prescribe", "contact us",
    "straightaway", "severe", "unrelenting",
    # Patient instructions
    "advised to", "instructed to", "recommended to", "to continue",
    "to start", "to stop", "to avoid", "to use", "to take",
    # Follow-up instructions
    "review in", "return in", "follow up in", "check in",
    "appointment in", "see in", "reassess in",
    # Safety netting
    "if symptoms worsen", "if no improvement", "warning signs",
    "red flags", "when to seek help", "emergency signs"
]

# ─────────────────────── note‐parsing logic ───────────────────────
def classify_section(para: str, current_section: str, context_stack: List[str]) -> str:
    """
    Classify a paragraph into the appropriate SOAP section based on its content and context.
    """
    para_lower = para.lower()
    
    # Check for explicit section headers first
    for section, pattern in SOAP_RE.items():
        if pattern.search(para):
            return section
            
    # Check for plan patterns
    if any(pattern.lower() in para_lower for pattern in PLAN_PATTERNS):
        return "plan"
        
    # Check for assessment patterns
    if any(pattern.lower() in para_lower for pattern in ASSESSMENT_PATTERNS):
        return "assessment"
        
    # Look for history blocks which are part of subjective
    if any(x in para for x in ["PMH:", "DHx:", "SH:", "ICE:", "FH:", "NKDA"]):
        return "subjective"
        
    # Check for examination sections
    if any(x in para for x in ["Systemically well", "Systemically", "O/E:", "On examination", "Ex:", "Exam:"]):
        return "objective"
        
    # Handle system reviews
    if any(x.lower() in para_lower for x in ["chest", "heart", "breathing", "head", "throat", "ear", "eye"]):
        if para_lower.startswith(("no ", "feels ", "normal ")):
            return "objective"
            
    # Handle symptoms and physical findings
    if any(pattern.lower() in para_lower for pattern in OBJECTIVE_PATTERNS):
        # If it's clearly a measurement or finding, it's objective
        if any(x in para_lower for x in ["temp", "pulse", "bp", "sats", "weight", "height"]):
            return "objective"
        # If it's in the history context, keep it subjective
        if context_stack and context_stack[-1] == "history":
            return "subjective"
        # If it contains severity or measurements, it's objective
        if any(x in para_lower for x in ["severity", "/10", "cm", "mm", "kg", "°"]):
            return "objective"
        # Default to objective for physical findings
        return "objective"
        
    # Handle temporal information and patient concerns
    if any(x in para for x in ["/52 ago", "/7 ago", "Pt worried", "patient worried", "concerned about"]):
        return "subjective"
        
    # Keep current section if no strong indicators
    return current_section

def split_soap(note: str, presenting: Optional[str] = None) -> Dict[str, str]:
    """
    Heuristically split a free-text consultation note into S/O/A/P sections.
    
    Args:
        note: The full text of the consultation note
        presenting: Optional presenting complaint to prepend to subjective section
        
    Returns:
        Dictionary with keys 'subjective', 'objective', 'assessment', 'plan'
        containing the respective sections of the SOAP note.
    """
    # Initialize sections
    sections = {
        "subjective": [],
        "objective": [],
        "assessment": [],
        "plan": []
    }
    
    # Split note into paragraphs and lines
    paragraphs = []
    current_para = []
    
    for line in note.split("\n"):
        line = line.strip()
        if not line:
            if current_para:
                paragraphs.append("\n".join(current_para))
                current_para = []
        else:
            current_para.append(line)
    
    if current_para:
        paragraphs.append("\n".join(current_para))
    
    # Track the current section we're in
    current_section = "subjective"
    
    # Process each paragraph
    for i, para in enumerate(paragraphs):
        if not para:
            continue
        
        # Split paragraph into lines for better processing
        lines = para.split("\n")
        para_lower = para.lower()
        
        # Check for explicit section headers first
        section_found = False
        for section, pattern in SOAP_RE.items():
            if pattern.search(para):
                current_section = section
                # Handle special case of assessment patterns in the same line
                if section == "assessment" and "?" in para:
                    sections[section].append(para)
                else:
                    # Remove the header and keep the content
                    content = re.sub(pattern, "", para).strip()
                    if content:
                        sections[section].append(content)
                section_found = True
                break
        
        if section_found:
            continue
            
        # Check for PMH/DHx/SH/ICE sections (subjective)
        if any(x in para for x in ["PMH:", "DHx:", "SH:", "ICE:", "FH:", "NKDA"]):
            current_section = "subjective"
            sections["subjective"].append(para)
            continue
            
        # Check for Imp/Assessment section with diagnostic uncertainty
        if any(x in para_lower for x in ["need to exclude", "rule out", "? ", "query", "possible"]):
            current_section = "assessment"
            sections["assessment"].append(para)
            continue
            
        # Check for Plan section with numbered items
        if re.match(r'^\d+\.?\s', para):
            current_section = "plan"
            # Remove numbering and clean up
            content = re.sub(r'^\d+\.?\s*', '', para)
            sections["plan"].append(content)
            continue
            
        # Special handling for first two paragraphs
        if i < 2:
            # Split the paragraph into sentences
            sentences = [s.strip() for s in re.split(r'[.!?]+', para) if s.strip()]
            
            for sentence in sentences:
                sentence_lower = sentence.lower()
                
                # Check if this is a system review or examination finding
                if any(x in sentence_lower for x in [
                    "systemically", "no fevers", "no vomiting", "no sob",
                    "on examination", "o/e:", "ex:", "exam:",
                    "rs:", "gi:", "neuro:", "ls:", "se:", "cvs:", "msk:",
                    "no chest pain", "no headache", "no visual", "no nausea",
                    "no bowel", "no urinary", "no rash", "looks well",
                    "appears well", "not in pain", "comfortable",
                    "erythema", "swelling", "tenderness"
                ]):
                    sections["objective"].append(sentence)
                # Check if this contains measurements or vital signs
                elif any(x in sentence_lower for x in [
                    "temp", "pulse", "bp", "sats", "weight", "height",
                    "bmi", "cm", "mm", "kg", "°"
                ]):
                    sections["objective"].append(sentence)
                # Check if this is an assessment
                elif any(x in sentence_lower for x in [
                    "need to exclude", "rule out", "? ", "query",
                    "possible", "probable", "suspected", "likely"
                ]):
                    sections["assessment"].append(sentence)
                # Otherwise, it's part of the history
                else:
                    sections["subjective"].append(sentence)
            continue
            
        # Check for examination findings (objective)
        if any(x in para for x in ["O/E:", "On examination", "Ex:", "Exam:", "Examination:"]):
            current_section = "objective"
            sections["objective"].append(para)
            continue
            
        # Check for system review headers (objective)
        if any(x in para for x in ["RS:", "GI:", "Neuro:", "LS:", "SE:", "CVS:", "MSK:"]):
            current_section = "objective"
            sections["objective"].append(para)
            continue
            
        # Add to current section
        sections[current_section].append(para)
    
    # Clean up and join sections
    out = {}
    for section, lines in sections.items():
        text = " ".join(lines)
        # Clean up common artifacts
        text = text.replace("PMH:", "Past Medical History:")
        text = text.replace("DHx:", "Drug History:")
        text = text.replace("SH:", "Social History:")
        text = text.replace("ICE:", "Ideas/Concerns/Expectations:")
        text = text.replace("FH:", "Family History:")
        text = text.replace("NKDA", "No Known Drug Allergies")
        text = text.replace("Systemically well", "Systemic examination:")
        text = text.replace("Systemically", "Systemic examination:")
        text = text.replace("Conservative mx", "Conservative management")
        text = text.replace("INB", "if not better")
        text = text.replace("sx", "symptoms")
        text = text.replace("Rx", "treatment")
        text = text.replace("abdo", "abdominal")
        text = text.replace("FU", "follow up")
        text = text.replace("FU:", "follow up:")
        text = text.replace("FU ", "follow up ")
        text = text.replace("O/E:", "On examination:")
        text = text.replace("Ex:", "Examination:")
        text = text.replace("Exam:", "Examination:")
        text = text.replace("RS:", "Respiratory System:")
        text = text.replace("GI:", "Gastrointestinal System:")
        text = text.replace("Neuro:", "Neurological System:")
        text = text.replace("LS:", "Locomotor System:")
        text = text.replace("SE:", "Systemic Examination:")
        text = text.replace("CVS:", "Cardiovascular System:")
        text = text.replace("MSK:", "Musculoskeletal System:")
        text = text.replace("Hx:", "History:")
        text = text.replace("H/O:", "History of:")
        text = text.replace("Imp:", "Impression:")
        text = text.replace("Pln:", "Plan:")
        text = text.replace("DDx:", "Differential Diagnosis:")
        text = text.replace("Dx:", "Diagnosis:")
        out[section] = clean(text)
    
    # Prepend presenting complaint to Subjective if available
    if presenting:
        out["subjective"] = (
            f"Presenting complaint: {presenting}. " + out.get("subjective", "")
        ).strip()
    
    # Ensure all four keys exist, using placeholders when missing
    for k in ("subjective", "objective", "assessment", "plan"):
        out[k] = out.get(k) or PLACEHOLDER[k]
    
    return out

# ───────────────────────────── main loop ──────────────────────────
def main():
    """Process all consultation transcripts and notes to create the dataset."""
    # Get all doctor transcripts
    doctor_files = list(TRANS_DIR.glob("*_doctor.TextGrid"))
    total_files = len(doctor_files)
    processed = 0
    skipped = 0

    with OUTFILE.open("w", encoding="utf-8") as fout:
        for doc_grid in doctor_files:
            consultation_id = get_consultation_id(doc_grid)
            pat_grid = doc_grid.with_name(f"{consultation_id}_patient.TextGrid")
            note_json = NOTES_DIR / f"{consultation_id}.json"

            # Validate all required files exist
            if not pat_grid.exists():
                print(f"WARNING: Missing patient transcript for {consultation_id} — skipped")
                skipped += 1
                continue
            if not note_json.exists():
                print(f"WARNING: Missing SOAP note for {consultation_id} — skipped")
                skipped += 1
                continue

            try:
                # Build transcript
                doc_utts = parse_grid(doc_grid, "DOCTOR")
                pat_utts = parse_grid(pat_grid, "PATIENT")
                
                if not doc_utts and not pat_utts:
                    print(f"WARNING: No utterances found in {consultation_id} — skipped")
                    skipped += 1
                    continue
                    
                transcript = "\n".join(u for _, u in sorted(doc_utts + pat_utts, key=lambda x: x[0])).strip()

                # Build gold SOAP
                with note_json.open(encoding="utf-8") as f:
                    note_data = json.load(f)
                    if isinstance(note_data, str):
                        note_data = json.loads(note_data)
                
                soap = split_soap(
                    note_data.get("note", ""),
                    presenting=note_data.get("presenting_complaint")
                )

                # Write to output file
                json.dump({"input": transcript, "expected": soap},
                          fout, ensure_ascii=False)
                fout.write("\n")
                processed += 1

            except Exception as e:
                print(f"ERROR: Failed to process {consultation_id}: {str(e)}")
                skipped += 1
                continue

    print(f"Processing complete:")
    print(f"- Total consultations: {total_files}")
    print(f"- Successfully processed: {processed}")
    print(f"- Skipped: {skipped}")
    print(f"Dataset written to: {OUTFILE}")

if __name__ == "__main__":
    main()