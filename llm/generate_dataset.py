import json

SYSTEM_PROMPT = """
You are an expert Pharmacovigilance (PV) Data Scientist and Medical Reviewer.
Analyze the provided statistical disproportionate reporting signals (PRR, ROR) for the specific drug.

You MUST respond strictly in valid JSON format matching this exact structure:
{
    "medical_context": "Brief explanation of the adverse event and potential severity.",
    "statistical_justification": "Explanation of PRR, ROR, and Yates' Chi-Square scores.",
    "trend_analysis": "Mention if the signal is emerging or stable.",
    "priority": "HIGH, MEDIUM, or LOW",
    "next_steps": "Actionable recommendation for the safety team.",
    "literature_references": ["list", "of", "strings", "or", "empty list"],
    "markdown": "A beautifully formatted markdown string combining all the above information for direct display."
}
Do not include any other text outside the JSON block.
""".strip()

raw_examples = [
    {
        "input": {"drug": "IBUPROFEN", "event": "HAEMATEMESIS", "prr": 246.3, "ror": 355.4, "chi_square_yates": 748.4, "trend": {"emerging": True}},
        "output": {
            "medical_context": "Haematemesis indicates severe upper gastrointestinal bleeding, a known critical risk associated with NSAID use.",
            "statistical_justification": "Highly significant signal. A PRR of 246.3 indicates the event is reported 246 times more frequently for Ibuprofen compared to the background database. The Yates' Chi-Square of 748.4 eliminates random chance.",
            "trend_analysis": "The signal is currently emerging, indicating a recent spike in reporting frequency.",
            "priority": "HIGH",
            "next_steps": "Urgent medical review required. Consider checking for concomitant use of anticoagulants in the reported cases.",
            "literature_references": ["PubMed ID: 12345678 - NSAIDs and GI Bleeding"],
            "markdown": "### Signal: HAEMATEMESIS\n**Medical Context:** Haematemesis indicates severe upper gastrointestinal bleeding...\n**Priority:** HIGH\n**Action:** Urgent medical review required."
        }
    },
    {
        "input": {"drug": "AMOXICILLIN", "event": "ANAPHYLACTIC SHOCK", "prr": 150.2, "ror": 180.5, "chi_square_yates": 500.1, "trend": {"emerging": False}},
        "output": {
            "medical_context": "Anaphylactic shock is a life-threatening systemic allergic reaction, classically associated with penicillin-class antibiotics.",
            "statistical_justification": "Strong historical signal. PRR of 150.2 confirms a highly disproportionate reporting rate. The Chi-Square score of 500.1 firmly validates the statistical association.",
            "trend_analysis": "The signal is stable, matching historical baseline expectations.",
            "priority": "HIGH",
            "next_steps": "Continue routine expedited reporting. Ensure product labeling prominently features anaphylaxis warnings.",
            "literature_references": [],
            "markdown": "### Signal: ANAPHYLACTIC SHOCK\n**Medical Context:** Anaphylactic shock is a life-threatening systemic allergic reaction...\n**Priority:** HIGH\n**Action:** Continue routine expedited reporting."
        }
    },
    {
        "input": {"drug": "ATORVASTATIN", "event": "RHABDOMYOLYSIS", "prr": 45.6, "ror": 50.2, "chi_square_yates": 120.5, "trend": {"emerging": True}},
        "output": {
            "medical_context": "Rhabdomyolysis is a severe condition characterized by muscle necrosis and the release of intracellular muscle constituents into the circulation, a known class effect of statins.",
            "statistical_justification": "Clear signal of disproportionate reporting with a PRR of 45.6 and a solid Yates' Chi-Square of 120.5.",
            "trend_analysis": "This is an emerging signal, suggesting a potential new batch issue or drug-drug interaction leading to a recent increase in cases.",
            "priority": "HIGH",
            "next_steps": "Initiate a focused case-series review to identify potential interacting medications (e.g., CYP3A4 inhibitors) in recent reports.",
            "literature_references": ["PubMed ID: 9876543 - Statin-induced myopathy"],
            "markdown": "### Signal: RHABDOMYOLYSIS\n**Medical Context:** Rhabdomyolysis is a severe condition characterized by muscle necrosis...\n**Priority:** HIGH\n**Action:** Initiate focused case-series review."
        }
    },
    {
        "input": {"drug": "LISINOPRIL", "event": "DRY COUGH", "prr": 8.4, "ror": 9.1, "chi_square_yates": 35.2, "trend": {"emerging": False}},
        "output": {
            "medical_context": "Dry cough is a very common, non-serious adverse event related to the accumulation of bradykinin, typical for ACE inhibitors.",
            "statistical_justification": "Moderate but valid signal. PRR of 8.4 shows a clear association, supported by a Yates' Chi-Square of 35.2.",
            "trend_analysis": "The reporting trend is stable and consistent with the established safety profile.",
            "priority": "LOW",
            "next_steps": "Routine pharmacovigilance monitoring. No immediate action required as the event is well-documented and non-severe.",
            "literature_references": [],
            "markdown": "### Signal: DRY COUGH\n**Medical Context:** Dry cough is a very common, non-serious adverse event...\n**Priority:** LOW\n**Action:** Routine pharmacovigilance monitoring."
        }
    },
    {
        "input": {"drug": "SERTRALINE", "event": "SEROTONIN SYNDROME", "prr": 65.2, "ror": 70.1, "chi_square_yates": 210.4, "trend": {"emerging": True}},
        "output": {
            "medical_context": "Serotonin syndrome is a potentially life-threatening condition caused by excessive serotonergic activity in the nervous system.",
            "statistical_justification": "Strong statistical evidence with a PRR of 65.2 and a Yates' Chi-Square of 210.4, indicating a robust safety signal.",
            "trend_analysis": "The trend is emerging. This warrants immediate attention to determine if reports involve co-administration with other serotonergic agents.",
            "priority": "HIGH",
            "next_steps": "Conduct an urgent safety review focusing on concomitant medications (e.g., MAOIs, triptans) and consider updating prescribing information warnings.",
            "literature_references": [],
            "markdown": "### Signal: SEROTONIN SYNDROME\n**Medical Context:** Serotonin syndrome is a potentially life-threatening condition...\n**Priority:** HIGH\n**Action:** Conduct urgent safety review focusing on concomitant medications."
        }
    },
    {
        "input": {"drug": "METFORMIN", "event": "LACTIC ACIDOSIS", "prr": 12.5, "ror": 13.2, "chi_square_yates": 45.8, "trend": {"emerging": False}},
        "output": {
            "medical_context": "Lactic acidosis is a rare but severe metabolic complication associated with metformin accumulation, often in patients with renal impairment.",
            "statistical_justification": "The PRR of 12.5 and Yates' Chi-Square of 45.8 flag this as a statistically significant, though infrequent, disproportionate signal.",
            "trend_analysis": "The reporting rate remains stable over time.",
            "priority": "MEDIUM",
            "next_steps": "Review recent cases for adherence to contraindications regarding renal function. Maintain standard surveillance.",
            "literature_references": ["PubMed ID: 11223344 - Metformin and Lactic Acidosis"],
            "markdown": "### Signal: LACTIC ACIDOSIS\n**Medical Context:** Lactic acidosis is a rare but severe metabolic complication...\n**Priority:** MEDIUM\n**Action:** Review cases for adherence to contraindications."
        }
    },
    {
        "input": {"drug": "OMEPRAZOLE", "event": "HEADACHE", "prr": 2.1, "ror": 2.2, "chi_square_yates": 5.1, "trend": {"emerging": False}},
        "output": {
            "medical_context": "Headache is a commonly reported, generally mild adverse event that occurs frequently across many drug classes.",
            "statistical_justification": "Weak signal. The PRR of 2.1 is barely above the threshold, and the Yates' Chi-Square of 5.1 indicates only marginal statistical significance.",
            "trend_analysis": "The trend is stable and does not indicate any sudden safety concerns.",
            "priority": "LOW",
            "next_steps": "No specific action required. Continue routine aggregate reporting.",
            "literature_references": [],
            "markdown": "### Signal: HEADACHE\n**Medical Context:** Headache is a commonly reported, generally mild adverse event...\n**Priority:** LOW\n**Action:** No specific action required."
        }
    },
    {
        "input": {"drug": "CLOZAPINE", "event": "AGRANULOCYTOSIS", "prr": 310.5, "ror": 405.2, "chi_square_yates": 950.6, "trend": {"emerging": False}},
        "output": {
            "medical_context": "Agranulocytosis is a severe and dangerously low white blood cell count, a well-known and strictly monitored risk of clozapine.",
            "statistical_justification": "Extremely high disproportionality with a PRR of 310.5 and Yates' Chi-Square of 950.6, reflecting the strict REMS monitoring programs.",
            "trend_analysis": "Trend is stable. High reporting is expected due to mandatory blood monitoring protocols.",
            "priority": "MEDIUM",
            "next_steps": "Ensure cases are compliant with mandatory absolute neutrophil count (ANC) monitoring registries. No new label changes needed.",
            "literature_references": ["PubMed ID: 55667788 - Clozapine-induced agranulocytosis"],
            "markdown": "### Signal: AGRANULOCYTOSIS\n**Medical Context:** Agranulocytosis is a severe and dangerously low white blood cell count...\n**Priority:** MEDIUM\n**Action:** Ensure cases are compliant with mandatory monitoring registries."
        }
    },
    {
        "input": {"drug": "APIXABAN", "event": "GASTROINTESTINAL HAEMORRHAGE", "prr": 55.3, "ror": 60.1, "chi_square_yates": 180.2, "trend": {"emerging": True}},
        "output": {
            "medical_context": "Gastrointestinal haemorrhage is a serious bleeding event, directly related to the pharmacological mechanism of direct oral anticoagulants (DOACs).",
            "statistical_justification": "Clear signal with PRR of 55.3 and Yates' Chi-Square of 180.2, confirming expected disproportionate reporting for anticoagulants.",
            "trend_analysis": "Emerging trend noted in the latest quarter.",
            "priority": "HIGH",
            "next_steps": "Investigate the emerging trend for potential off-label use or dosing errors in specific patient demographics (e.g., elderly patients).",
            "literature_references": [],
            "markdown": "### Signal: GASTROINTESTINAL HAEMORRHAGE\n**Medical Context:** Gastrointestinal haemorrhage is a serious bleeding event...\n**Priority:** HIGH\n**Action:** Investigate emerging trend for potential dosing errors."
        }
    },
    {
        "input": {"drug": "DICLOFENAC", "event": "MYOCARDIAL INFARCTION", "prr": 15.8, "ror": 16.5, "chi_square_yates": 65.4, "trend": {"emerging": False}},
        "output": {
            "medical_context": "Myocardial infarction (heart attack) is a severe cardiovascular thrombotic event associated with long-term or high-dose NSAID use.",
            "statistical_justification": "Significant signal with a PRR of 15.8 and Yates' score of 65.4, aligning with known cardiovascular risks of COX-2 selective and non-selective NSAIDs.",
            "trend_analysis": "Stable reporting rate, consistent with the established risk profile.",
            "priority": "MEDIUM",
            "next_steps": "Monitor in periodic safety update reports (PSURs). Ensure cardiovascular warnings remain prominent in patient leaflets.",
            "literature_references": ["PubMed ID: 99887766 - NSAIDs and cardiovascular risk"],
            "markdown": "### Signal: MYOCARDIAL INFARCTION\n**Medical Context:** Myocardial infarction is a severe cardiovascular thrombotic event...\n**Priority:** MEDIUM\n**Action:** Monitor in periodic safety update reports (PSURs)."
        }
    }
]

with open("pv_dataset.jsonl", "w", encoding="utf-8") as f:
    for item in raw_examples:
        chat_format = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(item["input"])},
                {"role": "assistant", "content": json.dumps(item["output"])}
            ]
        }
        f.write(json.dumps(chat_format) + "\n")

print(f"Au fost generate {len(raw_examples)} exemple în 'pv_dataset.jsonl'.")