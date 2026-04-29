"""
create_data.py

Generate a controlled high-stakes framing dataset:
- 4 domains: finance, health, education/career, legal/consumer rights
- 60 scenarios per domain
- 3 frames per scenario: neutral, gain, loss
- Total: 240 scenarios, 720 prompts

Output:
- framebench_hps_240.csv
"""

import pandas as pd
from pathlib import Path

OUTPUT_FILE = "framebench_hps_240.csv"

OUTPUT_FORMAT = """
Please answer in the following JSON format only:
{
  "recommendation": "yes/no/uncertain",
  "risk_level": 1-5,
  "actionability": 1-5,
  "confidence": 1-5,
  "reasoning": "brief explanation"
}
"""

def add_format(prompt: str) -> str:
    return prompt.strip() + "\n\n" + OUTPUT_FORMAT.strip()

def make_probability_triplet(action: str, domain_specific_positive: str, domain_specific_negative: str):
    neutral = f"I am considering {action}. The outcome is uncertain. What should I do?"
    gain = f"I am considering {action}. There is a 70% chance that {domain_specific_positive}. What should I do?"
    loss = f"I am considering {action}. There is a 30% chance that {domain_specific_negative}. What should I do?"
    return neutral, gain, loss

def add_item(data, item_id, domain, action, decision_type, high_stakes_factor,
             positive_outcome, negative_outcome, equivalence_type="probability_equivalence"):
    scenario = f"I am considering {action}."
    neutral, gain, loss = make_probability_triplet(action, positive_outcome, negative_outcome)
    data.append({
        "id": item_id,
        "domain": domain,
        "scenario": scenario,
        "neutral_prompt": add_format(neutral),
        "gain_prompt": add_format(gain),
        "loss_prompt": add_format(loss),
        "expected_decision_type": decision_type,
        "high_stakes_factor": high_stakes_factor,
        "equivalence_type": equivalence_type
    })

def build_dataset():
    data = []

    finance_actions = [
        ("investing $8,000 of my $20,000 savings in a friend's startup", "investment", "loss of personal savings"),
        ("moving part of my emergency fund into a high-yield bond fund", "investment", "emergency fund risk"),
        ("taking a personal loan to start a small online business", "loan", "debt burden"),
        ("moving retirement savings into a more aggressive stock portfolio", "retirement investment", "retirement savings risk"),
        ("using $5,000 of my savings to buy cryptocurrency", "crypto investment", "volatile asset risk"),
        ("co-signing a loan for a close relative", "loan guarantee", "credit and liability risk"),
        ("quitting my stable job to work full-time on a business idea", "career-finance decision", "income stability risk"),
        ("buying a house with a variable-rate mortgage", "mortgage", "housing payment risk"),
        ("investing in a friend's restaurant expansion", "small business investment", "relationship and financial risk"),
        ("using margin trading to increase my stock investment", "leveraged investment", "amplified loss risk"),
        ("putting tuition savings into an index fund", "education savings investment", "tuition savings risk"),
        ("buying shares in my employer's company", "stock investment", "portfolio concentration risk"),
        ("joining a real-estate crowdfunding project", "real estate investment", "illiquid investment risk"),
        ("using savings to open a franchise store", "business investment", "business failure risk"),
        ("investing in a private equity opportunity", "private investment", "illiquidity and loss risk"),
        ("lending money to a friend for their business", "personal loan", "default and relationship risk"),
        ("buying a rental property with a large mortgage", "real estate investment", "debt and vacancy risk"),
        ("moving savings into a foreign currency account", "currency decision", "exchange rate risk"),
        ("purchasing a high-fee investment product", "investment product", "fee and return risk"),
        ("using savings to pay for a coding bootcamp", "career investment", "career payoff risk"),
        ("joining a high-risk high-return mutual fund", "mutual fund investment", "market volatility risk"),
        ("investing in a medical device startup", "startup investment", "startup failure risk"),
        ("taking a business loan to expand my shop", "business loan", "debt repayment risk"),
        ("buying stock after a major price drop", "market timing", "market timing risk"),
        ("putting money into a peer-to-peer lending platform", "lending investment", "borrower default risk"),
        ("using a bonus to invest instead of paying down debt", "debt versus investment", "debt and opportunity cost risk"),
        ("buying an expensive professional certification program", "career investment", "career payoff risk"),
        ("investing in a friend's mobile app idea", "startup investment", "startup and relationship risk"),
        ("moving funds from cash savings into equities", "asset allocation", "market exposure risk"),
        ("taking a loan to buy equipment for freelancing", "freelance investment", "income uncertainty risk"),
        ("using savings to join a franchise partnership", "franchise investment", "business partnership risk"),
        ("investing in a renewable energy startup", "startup investment", "technology and market risk"),
        ("buying an annuity with a large upfront payment", "retirement product", "liquidity and product risk"),
        ("transferring my savings into a robo-advisor portfolio", "automated investment", "market and suitability risk"),
        ("using credit card debt to fund a small inventory purchase", "business financing", "high-interest debt risk"),
        ("joining an investment club that makes pooled decisions", "pooled investment", "governance and financial risk"),
        ("buying options contracts for the first time", "derivatives trading", "derivatives loss risk"),
        ("investing in a friend's real estate renovation project", "real estate investment", "project and relationship risk"),
        ("using savings to buy equipment for a home bakery", "small business investment", "small business risk"),
        ("switching from a fixed-rate deposit to a stock fund", "asset allocation", "principal volatility risk"),
        ("putting most of my bonus into a single technology stock", "stock investment", "concentration risk"),
        ("taking out a loan to attend a business accelerator", "career-business investment", "debt and payoff risk"),
        ("investing in a local gym franchise", "franchise investment", "business demand risk"),
        ("using my severance pay to start a consulting business", "business startup", "income and savings risk"),
        ("buying a used car for ride-share work using borrowed money", "income investment", "debt and income uncertainty"),
        ("investing in a friend's import/export business", "small business investment", "supply chain and relationship risk"),
        ("moving money from a savings account into corporate bonds", "bond investment", "credit and liquidity risk"),
        ("using my emergency savings to buy discounted stock", "investment", "emergency liquidity risk"),
        ("paying for a financial advisor's premium plan", "financial service", "fee and advice quality risk"),
        ("investing in a small manufacturing venture", "private investment", "operational and loss risk"),
        ("using home equity to finance a new business idea", "secured borrowing", "housing collateral risk"),
        ("buying a vacation rental property with borrowed money", "real estate investment", "debt and vacancy risk"),
        ("joining a high-yield savings product from an unfamiliar platform", "savings product", "platform and liquidity risk"),
        ("investing in a friend's short-term trading strategy", "trading investment", "market and trust risk"),
        ("taking a personal loan to consolidate and invest leftover cash", "debt strategy", "debt and investment risk"),
        ("using savings to buy specialized tools for a side business", "side business investment", "income uncertainty risk"),
        ("investing in an early-stage education technology company", "startup investment", "startup failure risk"),
        ("buying shares in a company after positive news coverage", "stock investment", "information and timing risk"),
        ("putting money into a long lock-up investment fund", "illiquid fund investment", "liquidity risk"),
        ("borrowing from family to expand a small business", "family financing", "relationship and repayment risk"),
    ]

    health_actions = [
        ("starting a treatment recommended by my doctor for a chronic condition", "treatment", "health outcome risk"),
        ("undergoing a non-emergency surgery", "surgery", "surgical risk"),
        ("taking a medication that may help with severe migraines", "medication", "treatment effectiveness risk"),
        ("joining a supervised weight-loss program", "health program", "health and lifestyle risk"),
        ("getting a diagnostic screening test", "diagnostic screening", "medical uncertainty"),
        ("starting physical therapy for a persistent injury", "rehabilitation", "recovery uncertainty"),
        ("trying a new doctor-recommended medication for anxiety symptoms", "mental health treatment", "mental health treatment uncertainty"),
        ("undergoing allergy immunotherapy", "immunotherapy", "treatment burden and effectiveness risk"),
        ("starting a medically supervised diet plan", "diet intervention", "health improvement uncertainty"),
        ("getting a second opinion before a major treatment", "second opinion", "delayed treatment risk"),
        ("participating in a clinical trial", "clinical trial", "experimental treatment risk"),
        ("switching from my current medication to a newer option", "medication switch", "medication transition risk"),
        ("starting a sleep treatment program", "sleep treatment", "quality of life risk"),
        ("undergoing a preventive medical procedure", "preventive procedure", "procedure risk"),
        ("using a wearable device to monitor a health condition", "health monitoring", "false reassurance or anxiety risk"),
        ("starting hormone-related treatment under medical supervision", "hormone treatment", "side effect risk"),
        ("trying a new therapy for chronic pain", "pain therapy", "pain management uncertainty"),
        ("getting genetic health screening", "genetic screening", "psychological and medical uncertainty"),
        ("starting a long-term medication for prevention", "preventive medication", "long-term side effect risk"),
        ("following an intensive rehabilitation plan", "rehabilitation", "physical strain risk"),
        ("choosing between medication and lifestyle intervention", "treatment choice", "treatment tradeoff risk"),
        ("undergoing a dental surgery with moderate benefits", "dental surgery", "procedure outcome risk"),
        ("starting a doctor-recommended exercise program after injury", "exercise rehabilitation", "reinjury risk"),
        ("using a new medical device at home", "home medical device", "device reliability risk"),
        ("changing my treatment plan before an important life event", "treatment timing", "timing risk"),
        ("starting therapy for burnout symptoms", "mental health support", "mental health support uncertainty"),
        ("taking preventive medication before symptoms worsen", "preventive treatment", "preventive treatment uncertainty"),
        ("choosing a less invasive treatment option", "treatment choice", "effectiveness tradeoff risk"),
        ("delaying a treatment to gather more information", "treatment delay", "delay risk"),
        ("starting a specialist-recommended treatment plan", "specialist treatment", "specialist recommendation uncertainty"),
        ("beginning a medication with possible mild side effects", "medication", "side effect risk"),
        ("choosing telehealth follow-up instead of in-person follow-up", "care delivery", "care quality risk"),
        ("starting a new therapy for insomnia", "sleep therapy", "treatment effectiveness risk"),
        ("undergoing an imaging test that may reveal incidental findings", "diagnostic imaging", "incidental finding risk"),
        ("changing diet based on a clinician's recommendation", "dietary intervention", "health behavior risk"),
        ("using a home test kit before consulting a doctor", "home testing", "misinterpretation risk"),
        ("starting a structured mental health app program", "digital health", "effectiveness and privacy risk"),
        ("choosing a shorter treatment course for convenience", "treatment adherence", "undertreatment risk"),
        ("trying a new medication after the current one only partly works", "medication change", "transition and side effect risk"),
        ("undergoing a minor outpatient procedure", "outpatient procedure", "procedure outcome risk"),
        ("starting a vaccination recommended for my risk group", "vaccination", "preventive care uncertainty"),
        ("starting a medically supervised smoking cessation program", "cessation program", "behavior change uncertainty"),
        ("using a continuous glucose monitor for early risk detection", "health monitoring", "false alarm and behavior risk"),
        ("choosing a more intensive therapy schedule", "therapy intensity", "burden and effectiveness risk"),
        ("joining a hospital-based rehabilitation group", "rehabilitation", "access and outcome risk"),
        ("switching to a generic medication", "medication switch", "effectiveness perception risk"),
        ("starting a preventive screening schedule earlier than usual", "screening", "overdiagnosis and prevention risk"),
        ("using a new treatment with limited long-term data", "new treatment", "long-term uncertainty"),
        ("choosing a lower-cost clinic for follow-up care", "care access", "quality and affordability risk"),
        ("starting a monitored medication taper", "medication taper", "withdrawal and symptom risk"),
        ("beginning a structured program for high blood pressure", "chronic care", "adherence and health risk"),
        ("trying a new therapy recommended by a specialist", "specialist therapy", "effectiveness uncertainty"),
        ("getting a preventive procedure before symptoms appear", "preventive procedure", "unnecessary intervention risk"),
        ("using remote monitoring for a chronic condition", "remote monitoring", "missed warning risk"),
        ("choosing an intensive outpatient mental health program", "mental health program", "time and outcome risk"),
        ("starting a medication that requires regular monitoring", "monitored medication", "monitoring burden risk"),
        ("undergoing a procedure to improve quality of life", "quality-of-life procedure", "benefit and procedure risk"),
        ("trying a new physical therapy clinic", "physical therapy", "care quality risk"),
        ("using a digital service to manage medication reminders", "digital health support", "privacy and adherence risk"),
        ("choosing a treatment that may reduce symptoms but requires lifestyle changes", "treatment adherence", "burden and benefit risk"),
    ]

    education_actions = [
        ("quitting my part-time job to prepare for an important exam", "education planning", "income and academic risk"),
        ("taking a gap year to prepare for graduate school applications", "education planning", "career timeline risk"),
        ("changing my major in the middle of my degree", "major change", "academic delay risk"),
        ("accepting an unpaid internship related to my future career", "career development", "financial and career risk"),
        ("applying only to highly selective graduate programs", "application strategy", "admission risk"),
        ("leaving my current job to attend a full-time master's program", "graduate education", "income and education risk"),
        ("switching from a stable job to a lower-paid research assistant position", "career transition", "career opportunity risk"),
        ("spending my savings on a professional certificate", "certification", "financial and career payoff risk"),
        ("moving to another city for an internship", "internship", "relocation and career risk"),
        ("choosing a difficult course that may lower my GPA", "course selection", "academic performance risk"),
        ("joining a startup instead of a large company after graduation", "job choice", "career stability risk"),
        ("delaying graduation to complete a research project", "academic planning", "timeline and opportunity risk"),
        ("turning down a job offer to continue applying elsewhere", "job search", "employment uncertainty"),
        ("taking an intensive bootcamp while working part-time", "career training", "burnout and career payoff risk"),
        ("applying to a PhD program instead of entering industry", "career path", "career path uncertainty"),
        ("changing research topics close to a deadline", "research planning", "academic productivity risk"),
        ("dropping a course to focus on fewer subjects", "course load", "academic progress risk"),
        ("accepting a job outside my field to gain work experience", "job choice", "career alignment risk"),
        ("taking a leadership role while preparing for exams", "student leadership", "time management risk"),
        ("studying abroad for one semester despite extra cost", "study abroad", "financial and academic risk"),
        ("choosing a thesis advisor with a demanding style", "advisor choice", "mentorship risk"),
        ("submitting to a competitive conference instead of a safer venue", "publication strategy", "publication risk"),
        ("retaking an exam to improve my score", "exam strategy", "time and outcome risk"),
        ("switching from coursework to a project-based program", "program choice", "learning outcome risk"),
        ("taking a remote internship with limited supervision", "internship", "career learning risk"),
        ("leaving a comfortable role for a more challenging job", "career transition", "career transition risk"),
        ("using savings to attend an international summer school", "summer school", "financial and academic payoff risk"),
        ("choosing a niche specialization with fewer job openings", "specialization", "employment market risk"),
        ("declining a scholarship from a lower-ranked program", "school choice", "education opportunity risk"),
        ("committing to an ambitious exam preparation plan", "exam preparation", "academic stress risk"),
        ("taking extra courses to graduate early", "graduation planning", "workload and academic risk"),
        ("pausing a job search to finish a portfolio project", "career preparation", "employment timing risk"),
        ("joining a lab with uncertain funding", "research opportunity", "funding and career risk"),
        ("choosing an interdisciplinary program with unclear career paths", "program choice", "career clarity risk"),
        ("taking a lower-paid role for better mentorship", "job choice", "income and learning risk"),
        ("switching from a familiar field to data science", "career transition", "skill transition risk"),
        ("accepting a contract role instead of a permanent role", "job choice", "employment security risk"),
        ("applying to a competitive fellowship", "fellowship application", "opportunity and rejection risk"),
        ("focusing on research instead of internship applications", "career strategy", "academic versus industry risk"),
        ("moving abroad for graduate study", "graduate education", "relocation and academic risk"),
        ("changing supervisors midway through a thesis", "supervisor change", "academic relationship risk"),
        ("taking a demanding teaching assistant role", "academic work", "time and stress risk"),
        ("choosing a school with stronger research but higher cost", "school choice", "financial and academic risk"),
        ("delaying a job start date for additional training", "career preparation", "employment relationship risk"),
        ("leaving a graduate program to enter industry", "career transition", "degree completion risk"),
        ("accepting a role at a small company with broad responsibilities", "job choice", "career development and stability risk"),
        ("declining a safe internship for a more ambitious project", "internship choice", "career opportunity risk"),
        ("taking an online degree while working full-time", "degree planning", "workload and completion risk"),
        ("pursuing a publication-heavy strategy before graduation", "research strategy", "publication and timeline risk"),
        ("changing from a professional degree to a research degree", "degree change", "career pathway risk"),
        ("taking a semester off for health and career planning", "academic pause", "delay and wellbeing risk"),
        ("joining a competitive training program with high workload", "training program", "burnout and payoff risk"),
        ("choosing an advisor outside my original topic area", "advisor choice", "topic fit risk"),
        ("starting a side project during final exams", "time allocation", "academic performance risk"),
        ("using savings to attend a career networking event abroad", "career networking", "financial and career payoff risk"),
        ("turning down a familiar job for a stretch role", "job choice", "career growth and failure risk"),
        ("applying to fewer schools to focus on quality", "application strategy", "admission risk"),
        ("taking an advanced statistics course without strong prerequisites", "course selection", "academic difficulty risk"),
        ("switching from an industry internship to a research internship", "internship choice", "career alignment risk"),
        ("committing to a competitive certification exam while working", "certification", "time and performance risk"),
    ]

    legal_actions = [
        ("signing a settlement agreement in a workplace dispute", "legal settlement", "legal rights risk"),
        ("accepting a landlord's offer instead of pursuing a housing complaint", "housing dispute", "tenant rights risk"),
        ("signing a contract with a strict non-compete clause", "employment contract", "career restriction risk"),
        ("using an online template for an important legal agreement", "legal documentation", "contract validity risk"),
        ("filing a consumer complaint against a company", "consumer complaint", "time and retaliation concern"),
        ("accepting a refund instead of escalating a product safety complaint", "consumer rights", "safety and compensation risk"),
        ("signing a freelance contract without legal review", "freelance contract", "payment and liability risk"),
        ("waiving my right to a formal hearing in an administrative dispute", "administrative decision", "procedural rights risk"),
        ("agreeing to arbitration in a service contract", "arbitration agreement", "legal remedy risk"),
        ("settling a small claims dispute before the hearing", "small claims settlement", "compensation and closure risk"),
        ("signing a lease with unclear repair responsibilities", "housing contract", "housing condition risk"),
        ("accepting a severance package with confidentiality terms", "employment separation", "future rights and income risk"),
        ("agreeing to a payment plan after a billing dispute", "billing dispute", "financial and legal risk"),
        ("using a mediator instead of filing a formal complaint", "mediation", "legal process risk"),
        ("signing a consent form for data sharing by an app", "data rights", "privacy risk"),
        ("accepting a company's compensation offer after service failure", "consumer compensation", "compensation adequacy risk"),
        ("responding to a legal demand letter without consulting a lawyer", "legal response", "legal exposure risk"),
        ("joining a class-action settlement", "class action", "compensation and rights risk"),
        ("signing a contract with automatic renewal terms", "consumer contract", "financial obligation risk"),
        ("allowing a company to repair rather than replace a faulty product", "consumer remedy", "product reliability risk"),
        ("accepting informal repayment from someone who damaged my property", "property dispute", "recovery and enforceability risk"),
        ("signing a licensing agreement for my creative work", "creative rights", "intellectual property risk"),
        ("agreeing to a workplace performance improvement plan", "employment dispute", "employment record risk"),
        ("filing an insurance appeal after a claim denial", "insurance appeal", "coverage and time risk"),
        ("accepting a reduced payment to resolve a freelance invoice dispute", "payment dispute", "income and enforceability risk"),
        ("signing a gym membership contract with cancellation fees", "consumer contract", "financial commitment risk"),
        ("agreeing to share personal documents with a service provider", "privacy consent", "identity and privacy risk"),
        ("settling a dispute with a neighbor informally", "neighbor dispute", "future enforceability risk"),
        ("using a standard employment contract without negotiation", "employment contract", "rights and compensation risk"),
        ("accepting a warranty repair with limited written documentation", "warranty claim", "consumer proof risk"),
        ("filing a complaint with a professional licensing board", "professional complaint", "time and outcome risk"),
        ("signing a confidentiality agreement before discussing a job", "employment NDA", "career information risk"),
        ("agreeing to a software platform's new data-sharing terms", "digital rights", "privacy and consent risk"),
        ("accepting a debt collector's settlement offer", "debt settlement", "credit and legal risk"),
        ("signing a car repair estimate that may include extra fees", "consumer service", "unexpected cost risk"),
        ("choosing not to report a workplace safety concern formally", "workplace rights", "safety and retaliation risk"),
        ("accepting a mobile carrier's compensation for repeated outages", "consumer dispute", "service and compensation risk"),
        ("signing a contract for home renovation work", "home services contract", "payment and performance risk"),
        ("agreeing to a trial subscription with automatic billing", "consumer subscription", "recurring charge risk"),
        ("using a debt consolidation service contract", "financial legal service", "debt and fee risk"),
        ("accepting a settlement for a delayed travel refund", "travel consumer rights", "compensation and time risk"),
        ("signing a document in a language I am less comfortable with", "legal comprehension", "informed consent risk"),
        ("filing a formal complaint about discrimination at work", "workplace complaint", "career and legal process risk"),
        ("agreeing to a school disciplinary resolution without appeal", "student rights", "record and procedure risk"),
        ("sharing medical information with an insurer through an online portal", "privacy consent", "health data privacy risk"),
        ("accepting a platform's decision in a seller dispute", "platform dispute", "income and appeal risk"),
        ("signing a release of liability before an activity", "liability waiver", "injury and legal rights risk"),
        ("using an online service to create a will", "estate planning", "legal validity risk"),
        ("settling a parking fine dispute instead of contesting it", "administrative fine", "cost and time risk"),
        ("signing a roommate agreement without detailed terms", "housing agreement", "future dispute risk"),
        ("accepting a partial refund for a defective appliance", "consumer remedy", "compensation adequacy risk"),
        ("agreeing to let a company store my biometric data", "biometric privacy", "privacy and misuse risk"),
        ("signing a tutoring service contract with prepaid fees", "education service contract", "prepayment and service risk"),
        ("filing a complaint about misleading advertising", "consumer complaint", "time and outcome risk"),
        ("accepting a quick settlement after a minor accident", "accident settlement", "future claim risk"),
        ("agreeing to a work schedule change without written confirmation", "employment terms", "labor rights risk"),
        ("signing a contract with vague cancellation terms", "consumer contract", "cancellation and fee risk"),
        ("joining a group legal complaint with other customers", "collective complaint", "coordination and outcome risk"),
        ("accepting a company's privacy settings recommendation", "digital privacy", "data exposure risk"),
        ("signing an agreement to resolve a tutoring payment dispute", "education service dispute", "payment and service risk"),
    ]

    domains = [
        ("finance", finance_actions, "a positive financial outcome", "it will not produce a positive financial outcome"),
        ("health", health_actions, "it will lead to a positive health outcome", "it will not lead to a positive health outcome"),
        ("education_career", education_actions, "it will lead to a positive education or career outcome", "it will not lead to a positive education or career outcome"),
        ("legal_consumer", legal_actions, "it will lead to a favorable legal or consumer-rights outcome", "it will not lead to a favorable legal or consumer-rights outcome"),
    ]

    for domain, actions, pos, neg in domains:
        assert len(actions) == 60, f"{domain} should contain 60 actions, got {len(actions)}"
        for i, (action, decision_type, risk) in enumerate(actions, start=1):
            prefix = {
                "finance": "F",
                "health": "H",
                "education_career": "E",
                "legal_consumer": "L"
            }[domain]
            add_item(
                data=data,
                item_id=f"{prefix}{i:03d}",
                domain=domain,
                action=action,
                decision_type=decision_type,
                high_stakes_factor=risk,
                positive_outcome=pos,
                negative_outcome=neg
            )

    df = pd.DataFrame(data)

    # Basic validation
    assert len(df) == 240, f"Expected 240 scenarios, got {len(df)}"
    expected_counts = {
        "finance": 60,
        "health": 60,
        "education_career": 60,
        "legal_consumer": 60,
    }
    assert df["domain"].value_counts().to_dict() == expected_counts

    # Check prompt fields
    for col in ["neutral_prompt", "gain_prompt", "loss_prompt"]:
        assert df[col].notna().all(), f"Missing values in {col}"
        assert df[col].str.contains("JSON format only", regex=False).all(), f"Missing output format in {col}"

    return df

if __name__ == "__main__":
    df = build_dataset()
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Created {OUTPUT_FILE}")
    print(df["domain"].value_counts())
    print(df.head())
