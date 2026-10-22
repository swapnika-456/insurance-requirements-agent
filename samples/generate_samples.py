"""
==============================================================================
File: samples/generate_samples.py
Purpose: Generates 3 realistic synthetic insurance product PDF documents
         (Personal Auto Policy, Homeowners HO-3 Policy, and 20-Year Term Life Spec)
         used for ingestion, testing, citation verification, and benchmarking.
Architecture: Test & Evaluation Artifacts / Ingestion Pipeline Seed Data
==============================================================================

Why Synthetic Samples?
In enterprise insurance software delivery, real policy forms frequently contain
proprietary actuarial formulations, non-public filed rules, or PII. By synthesizing
realistic ISO-standard and carrier-grade policy forms, we test all parsing,
extraction, and citation capabilities safely without data privacy violations.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and print accurate total page numbers
    in the running footer (e.g., 'Page 2 of 4').
    
    Why this is needed:
    In insurance contracts, statutory compliance requires explicit 'Page X of Y'
    numbering to ensure no pages have been omitted or tampered with.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#4A5568"))
        
        # Header banner
        self.drawString(54, 750, "APEX MUTUAL INSURANCE COMPANY - CONFIDENTIAL PRODUCT SPECIFICATION")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 744, 558, 744)
        
        # Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 40, page_text)
        self.drawString(54, 40, "FOR TESTING & DELIVERY SPECIFICATION USE ONLY - NO PII CONTAINED")
        self.line(54, 52, 558, 52)
        self.restoreState()


def get_custom_styles():
    """Builds hierarchical paragraph styles designed for heading extraction."""
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        name='DocTitle',
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=12
    ))
    styles.add(ParagraphStyle(
        name='DocSubtitle',
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#334155"),
        spaceAfter=16
    ))
    styles.add(ParagraphStyle(
        name='SectionHeading',
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#1E3A8A"), # Deep Navy
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    ))
    styles.add(ParagraphStyle(
        name='ClauseHeading',
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#0284C7"), # Slate Blue
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    ))
    styles.add(ParagraphStyle(
        name='ClauseBody',
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name='TableLabel',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#0F172A")
    ))
    styles.add(ParagraphStyle(
        name='TableValue',
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#334155")
    ))
    return styles


def generate_auto_policy_pdf(output_path: str):
    """
    Generates a 3-page synthetic Personal Auto Policy Form (Form PA-2026-OH).
    Line of Business: Personal Auto
    Jurisdiction: State of Ohio
    Effective Date: January 1, 2026
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=60,
        bottomMargin=60
    )
    styles = get_custom_styles()
    story = []

    # Title & Metadata
    story.append(Paragraph("APEX PERSONAL AUTO POLICY FORM (PA-2026-OH)", styles['DocTitle']))
    story.append(Paragraph("Line of Business: Personal Auto | Jurisdiction: State of Ohio | Effective Date: January 1, 2026", styles['DocSubtitle']))
    story.append(Spacer(1, 8))

    # SECTION I - DECLARATIONS & SCHEDULE OF COVERAGES
    story.append(Paragraph("SECTION I - COVERAGE SCHEDULE & LIMITS", styles['SectionHeading']))
    story.append(Paragraph(
        "In return for payment of the premium and subject to all policy terms, Apex Mutual agrees to provide "
        "the coverages indicated below up to the specified limits of liability.", styles['ClauseBody']
    ))
    
    table_data = [
        [Paragraph("Coverage Description", styles['TableLabel']), 
         Paragraph("Stated Limit of Liability", styles['TableLabel']), 
         Paragraph("Applicable Deductible", styles['TableLabel'])],
        [Paragraph("Part A: Bodily Injury Liability", styles['TableValue']), 
         Paragraph("$250,000 per person / $500,000 per accident", styles['TableValue']), 
         Paragraph("None", styles['TableValue'])],
        [Paragraph("Part A: Property Damage Liability", styles['TableValue']), 
         Paragraph("$100,000 per accident", styles['TableValue']), 
         Paragraph("None", styles['TableValue'])],
        [Paragraph("Part B: Medical Payments", styles['TableValue']), 
         Paragraph("$5,000 per person", styles['TableValue']), 
         Paragraph("None", styles['TableValue'])],
        [Paragraph("Part C: Uninsured / Underinsured Motorist", styles['TableValue']), 
         Paragraph("$250,000 per person / $500,000 per accident", styles['TableValue']), 
         Paragraph("None", styles['TableValue'])],
        [Paragraph("Part D: Collision Coverage", styles['TableValue']), 
         Paragraph("Actual Cash Value (ACV)", styles['TableValue']), 
         Paragraph("$500 per occurrence", styles['TableValue'])],
        [Paragraph("Part D: Comprehensive / Other Than Collision", styles['TableValue']), 
         Paragraph("Actual Cash Value (ACV)", styles['TableValue']), 
         Paragraph("$250 per occurrence", styles['TableValue'])],
    ]
    t = Table(table_data, colWidths=[200, 180, 120])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F1F5F9")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    # SECTION II - INSURING AGREEMENT & CLAUSES
    story.append(Paragraph("SECTION II - INSURING AGREEMENTS & DEFINITIONS", styles['SectionHeading']))
    story.append(Paragraph("Clause 2.1: Bodily Injury and Property Damage Agreement", styles['ClauseHeading']))
    story.append(Paragraph(
        "Apex Mutual will pay damages for bodily injury or property damage for which any insured becomes legally responsible "
        "because of an auto accident. We will settle or defend, as we consider appropriate, any claim or suit asking for these damages.",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Clause 2.2: Collision and Comprehensive Repair Settlement", styles['ClauseHeading']))
    story.append(Paragraph(
        "Under Part D, our limit of liability for loss will be the lesser of the actual cash value of the stolen or damaged property, "
        "or the amount necessary to repair or replace the property with parts of like kind and quality. A mandatory deductible of $500 "
        "applies to all collision claims, and $250 applies to comprehensive events.",
        styles['ClauseBody']
    ))

    story.append(PageBreak()) # Page 2

    # SECTION III - RATING FACTORS & PREMIUM DETERMINATION
    story.append(Paragraph("SECTION III - ACTUARIAL RATING FACTORS & FORMULAS", styles['SectionHeading']))
    story.append(Paragraph(
        "Final premium is calculated by applying multiplicative rating factors to the base rate according to the formula: "
        "<b>Premium = BaseRate x DriverFactor x VehicleUsageFactor x TerritoryTierFactor x DrivingRecordPointsFactor</b>.",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Clause 3.1: Driver Age & Experience Rating Tiers", styles['ClauseHeading']))
    story.append(Paragraph(
        "Rating Factor RF-1 applies to driver age bands: Tier 1 (Ages 18-20, Factor 1.65), Tier 2 (Ages 21-24, Factor 1.30), "
        "Tier 3 (Ages 25-64, Factor 1.00 - Standard Baseline), and Tier 4 (Ages 65+, Factor 1.15).",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Clause 3.2: Territory Tiers (Ohio DOI Filings)", styles['ClauseHeading']))
    story.append(Paragraph(
        "Territory Factor RF-2 is based on vehicle garaging zip code: Territory 01 (Cuyahoga / Cleveland Metro, Factor 1.25), "
        "Territory 02 (Franklin / Columbus Urban, Factor 1.10), and Territory 03 (Rural Ohio Counties, Factor 0.85).",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Clause 3.3: Vehicle Usage Classification", styles['ClauseHeading']))
    story.append(Paragraph(
        "Factor RF-3 reflects vehicle usage: Pleasure (Factor 0.90), Commute under 15 miles (Factor 1.00), Commute 15+ miles (Factor 1.15), "
        "and Business Use (Factor 1.35). Delivery or gig rideshare requires specific Endorsement END-AUTO-04.",
        styles['ClauseBody']
    ))

    # SECTION IV - ELIGIBILITY & UNDERWRITING RULES
    story.append(Paragraph("SECTION IV - UNDERWRITING & ELIGIBILITY RULES", styles['SectionHeading']))
    story.append(Paragraph("Rule UW-1: Driver Licensing and Minimum Age", styles['ClauseHeading']))
    story.append(Paragraph(
        "All operators must possess a valid US or Canadian driver's license for a minimum of 12 consecutive months. "
        "The minimum driver age is 18 years. Operators with suspended or revoked licenses in the preceding 36 months are strictly ineligible.",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Rule UW-2: Violation and Moving Accident Thresholds", styles['ClauseHeading']))
    story.append(Paragraph(
        "Applicants with more than 1 at-fault accident or more than 2 moving violations within the prior 36 months cannot be bound "
        "without manual referral to an executive underwriter. Any major violation (DUI, vehicular manslaughter, reckless driving) "
        "within 60 months results in mandatory decline.",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Rule UW-3: Vehicle Age and Condition Constraints", styles['ClauseHeading']))
    story.append(Paragraph(
        "Private passenger autos older than 20 model years are not eligible for Part D Physical Damage (Collision/Comprehensive) "
        "without a certified mechanical inspection. Vehicles with existing unrepaired hail or collision damage are declined.",
        styles['ClauseBody']
    ))

    story.append(PageBreak()) # Page 3

    # SECTION V - EXCLUSIONS
    story.append(Paragraph("SECTION V - EXCLUSIONS & LIMITATIONS", styles['SectionHeading']))
    story.append(Paragraph("Clause 5.1: Intentional Loss and Criminal Acts", styles['ClauseHeading']))
    story.append(Paragraph(
        "We do not provide liability coverage for any insured who intentionally causes bodily injury or property damage, "
        "nor for losses arising from participation in organized racing, demolition contests, or criminal felonies.",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Clause 5.2: Commercial Rideshare and Unendorsed Delivery", styles['ClauseHeading']))
    story.append(Paragraph(
        "Coverage under Parts A, B, C, and D is excluded while the insured vehicle is logged into a transportation network platform "
        "(ridesharing, Uber, Lyft) or carrying property for delivery fee (DoorDash, Amazon Flex), unless modified by Endorsement END-AUTO-04.",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Clause 5.3: Nuclear and War Hazards", styles['ClauseHeading']))
    story.append(Paragraph(
        "This policy does not cover any loss, damage, or liability caused directly or indirectly by nuclear reaction, radiation, "
        "radioactive contamination, or acts of declared or undeclared war.",
        styles['ClauseBody']
    ))

    # SECTION VI - OPTIONAL POLICY ENDORSEMENTS
    story.append(Paragraph("SECTION VI - OPTIONAL ENDORSEMENTS & RIDERS", styles['SectionHeading']))
    story.append(Paragraph("Endorsement END-AUTO-01: 24/7 Roadside Assistance Service", styles['ClauseHeading']))
    story.append(Paragraph(
        "Provides towing up to 50 miles, battery jumpstarts, flat tire changes, fuel delivery, and lockout services. "
        "Maximum limit of $100 per service incident; limited to 4 disablement calls per annual policy term.",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Endorsement END-AUTO-02: Transportation Network / Rideshare Extension", styles['ClauseHeading']))
    story.append(Paragraph(
        "Extends comprehensive and collision coverage during Period 1 of TNC activity (driver logged on to app waiting for match). "
        "Requires a monthly endorsement surcharge of $28.00.",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Endorsement END-AUTO-03: Rental Vehicle Reimbursement", styles['ClauseHeading']))
    story.append(Paragraph(
        "Reimburses up to $40 per day to a maximum of $1,200 (30 days) for rental vehicle expenses incurred while the covered vehicle "
        "is inoperative due to a covered Part D loss.",
        styles['ClauseBody']
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated Auto Policy PDF: {output_path}")


def generate_homeowners_policy_pdf(output_path: str):
    """
    Generates a 3-page synthetic Homeowners HO-3 Special Form (Form HO3-2026-TX).
    Line of Business: Homeowners
    Jurisdiction: State of Texas
    Effective Date: March 1, 2026
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=60,
        bottomMargin=60
    )
    styles = get_custom_styles()
    story = []

    # Title & Metadata
    story.append(Paragraph("APEX HOMEOWNERS SPECIAL FORM HO-3 (HO3-2026-TX)", styles['DocTitle']))
    story.append(Paragraph("Line of Business: Homeowners | Jurisdiction: State of Texas | Effective Date: March 1, 2026", styles['DocSubtitle']))
    story.append(Spacer(1, 8))

    # SECTION I - PROPERTY COVERAGES & SCHEDULE
    story.append(Paragraph("SECTION I - PROPERTY COVERAGES & LIMIT SCHEDULE", styles['SectionHeading']))
    story.append(Paragraph(
        "Coverage under Section I protects against direct physical loss to property described in Coverages A, B, C, and D.",
        styles['ClauseBody']
    ))

    table_data = [
        [Paragraph("Section I / II Coverage", styles['TableLabel']), 
         Paragraph("Limit of Insurance", styles['TableLabel']), 
         Paragraph("Basis of Valuation / Limit Calculation", styles['TableLabel'])],
        [Paragraph("Coverage A: Dwelling", styles['TableValue']), 
         Paragraph("$450,000", styles['TableValue']), 
         Paragraph("Replacement Cost Value (RCV)", styles['TableValue'])],
        [Paragraph("Coverage B: Other Structures", styles['TableValue']), 
         Paragraph("$45,000", styles['TableValue']), 
         Paragraph("10% of Coverage A Dwelling Limit", styles['TableValue'])],
        [Paragraph("Coverage C: Personal Property", styles['TableValue']), 
         Paragraph("$225,000", styles['TableValue']), 
         Paragraph("50% of Coverage A Dwelling Limit (Actual Cash Value)", styles['TableValue'])],
        [Paragraph("Coverage D: Loss of Use", styles['TableValue']), 
         Paragraph("$90,000", styles['TableValue']), 
         Paragraph("20% of Coverage A Dwelling Limit", styles['TableValue'])],
        [Paragraph("Coverage E: Personal Liability", styles['TableValue']), 
         Paragraph("$300,000 per occurrence", styles['TableValue']), 
         Paragraph("Single limit bodily injury and property damage", styles['TableValue'])],
        [Paragraph("Coverage F: Medical Payments to Others", styles['TableValue']), 
         Paragraph("$5,000 per person", styles['TableValue']), 
         Paragraph("No-fault medical expenses within 3 years of accident", styles['TableValue'])],
    ]
    t = Table(table_data, colWidths=[180, 150, 170])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F1F5F9")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    # SECTION II - DEDUCTIBLES & LOSS SETTLEMENT
    story.append(Paragraph("SECTION II - DEDUCTIBLES & TEXAS SPECIAL PROVISIONS", styles['SectionHeading']))
    story.append(Paragraph("Clause 2.1: Standard All-Peril Deductible", styles['ClauseHeading']))
    story.append(Paragraph(
        "A baseline deductible of $1,500 applies to each covered loss under Section I, except for losses caused by Windstorm or Hail.",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Clause 2.2: Mandatory Texas Windstorm and Hail Deductible", styles['ClauseHeading']))
    story.append(Paragraph(
        "For properties located within the State of Texas, a separate Windstorm and Hail deductible applies equal to 2% "
        "of the Coverage A Dwelling limit ($9,000 for a $450,000 dwelling). No other deductible applies to windstorm or hail events.",
        styles['ClauseBody']
    ))

    story.append(PageBreak()) # Page 2

    # SECTION III - ACTUARIAL RATING FACTORS
    story.append(Paragraph("SECTION III - RATING FACTORS & RATE SCHEDULE", styles['SectionHeading']))
    story.append(Paragraph(
        "Base property insurance rate per $1,000 of Coverage A is modified by fire protection class, construction material, "
        "roof age, and coastal distance.",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Clause 3.1: ISO Public Protection Class (PPC) Factors", styles['ClauseHeading']))
    story.append(Paragraph(
        "Rating Factor RF-PPC applies according to municipal fire district grade: Class 1-3 (Factor 0.85), Class 4-6 (Factor 1.00 - Base), "
        "Class 7-8 (Factor 1.25), and Class 9-10 (Factor 1.70 - Requires underwriter pre-clearance).",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Clause 3.2: Construction Type & Roof Material Factors", styles['ClauseHeading']))
    story.append(Paragraph(
        "Masonry construction receives a credit factor of 0.90; Frame construction is base 1.00. Class 4 Impact-Resistant Roofs "
        "(UL 2218 certified) receive an annual premium reduction credit factor of 0.82.",
        styles['ClauseBody']
    ))

    # SECTION IV - UNDERWRITING & ELIGIBILITY GUIDELINES
    story.append(Paragraph("SECTION IV - UNDERWRITING RULES & BINDING AUTHORITY", styles['SectionHeading']))
    story.append(Paragraph("Rule UW-HO-1: Structure Age and Utility Modernization", styles['ClauseHeading']))
    story.append(Paragraph(
        "Dwellings older than 40 years are not eligible unless electrical (circuit breakers, no knob-and-tube), plumbing (copper/PEX), "
        "and HVAC systems have been fully updated within the last 20 years with permits. Polybutylene plumbing is unacceptable.",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Rule UW-HO-2: Roof Age and Maintenance Guidelines", styles['ClauseHeading']))
    story.append(Paragraph(
        "Roofs composed of architectural shingles must be under 20 years of age. Three-tab composite shingle roofs must be under "
        "15 years of age. Dwellings with existing wood shake roofs or curling/missing shingles are ineligible.",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Rule UW-HO-3: Coastal Territory Restriction (Texas Windstorm Insurance Association)", styles['ClauseHeading']))
    story.append(Paragraph(
        "Properties located Tier 1 first-tier coastal counties (Galveston, Brazoria, Nueces, etc.) must exclude wind/hail coverage "
        "and obtain windstorm policies via TWIA, or pay an Apex Coastal Surcharge Factor of 2.10.",
        styles['ClauseBody']
    ))

    story.append(PageBreak()) # Page 3

    # SECTION V - EXCLUSIONS
    story.append(Paragraph("SECTION V - EXCLUSIONS & RESTRICTIONS", styles['SectionHeading']))
    story.append(Paragraph("Clause 5.1: Water Damage & Flood Exclusion", styles['ClauseHeading']))
    story.append(Paragraph(
        "We do not cover loss caused directly or indirectly by: (1) flood, surface water, waves, tidal water, or storm surge; "
        "(2) water or water-borne material which backs up through sewers or drains or which overflows from a sump pump, "
        "unless explicitly endorsed under Endorsement HO-TX-04.",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Clause 5.2: Earth Movement and Sinkhole Collapse", styles['ClauseHeading']))
    story.append(Paragraph(
        "Excluded perils include earthquake, landslide, mudflow, subsidence, sinkhole collapse, or volcanic eruption.",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Clause 5.3: Foundation Settling and Soil Expansion", styles['ClauseHeading']))
    story.append(Paragraph(
        "We do not cover settling, cracking, shrinking, bulging or expansion of pavements, patios, foundations, walls, floors, "
        "roofs or ceilings caused by soil movement or thermal changes.",
        styles['ClauseBody']
    ))

    # SECTION VI - ENDORSEMENTS
    story.append(Paragraph("SECTION VI - COMMON ENDORSEMENTS", styles['SectionHeading']))
    story.append(Paragraph("Endorsement HO-TX-04: Water Backup and Sump Overflow", styles['ClauseHeading']))
    story.append(Paragraph(
        "Provides up to $10,000 for direct physical loss to property caused by water that backs up through sewers or drains "
        "or overflows from a sump pit. Subject to a dedicated $500 endorsement deductible. Annual premium: $65.00.",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Endorsement HO-TX-08: Scheduled Personal Property (Jewelry & Fine Arts)", styles['ClauseHeading']))
    story.append(Paragraph(
        "Provides open-peril scheduled coverage without deductible for specified jewelry, watches, furs, and fine arts "
        "up to an appraised schedule maximum of $25,000. Current appraisal within 24 months required.",
        styles['ClauseBody']
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated Homeowners Policy PDF: {output_path}")


def generate_term_life_spec_pdf(output_path: str):
    """
    Generates a 3-page synthetic 20-Year Level Term Life Insurance Product Specification (Spec TL-2026-IL).
    Line of Business: Life Insurance
    Jurisdiction: State of Illinois
    Effective Date: July 1, 2026
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=60,
        bottomMargin=60
    )
    styles = get_custom_styles()
    story = []

    # Title & Metadata
    story.append(Paragraph("APEX HORIZON 20-YEAR TERM LIFE PRODUCT SPECIFICATION (TL-2026-IL)", styles['DocTitle']))
    story.append(Paragraph("Line of Business: Term Life | Jurisdiction: State of Illinois | Effective Date: July 1, 2026", styles['DocSubtitle']))
    story.append(Spacer(1, 8))

    # SECTION I - PRODUCT SUMMARY & BENEFIT LIMITS
    story.append(Paragraph("SECTION I - PRODUCT SCOPE & BENEFIT SCHEDULE", styles['SectionHeading']))
    story.append(Paragraph(
        "The Horizon 20-Year Term Life product provides level death benefit protection for a guaranteed term of 20 years. "
        "Premiums remain level and guaranteed for the initial 20 policy years.", styles['ClauseBody']
    ))

    table_data = [
        [Paragraph("Product Attribute", styles['TableLabel']), 
         Paragraph("Specification Value", styles['TableLabel']), 
         Paragraph("Contract Definition", styles['TableLabel'])],
        [Paragraph("Plan Name", styles['TableValue']), 
         Paragraph("Apex Horizon 20 Level Term", styles['TableValue']), 
         Paragraph("Non-participating individual level term life insurance", styles['TableValue'])],
        [Paragraph("Issue Ages", styles['TableValue']), 
         Paragraph("Ages 18 to 65 (Age Nearest Birthday)", styles['TableValue']), 
         Paragraph("Terminates at policy anniversary nearest age 85", styles['TableValue'])],
        [Paragraph("Minimum Face Amount", styles['TableValue']), 
         Paragraph("$100,000", styles['TableValue']), 
         Paragraph("Minimum contract death benefit", styles['TableValue'])],
        [Paragraph("Maximum Face Amount", styles['TableValue']), 
         Paragraph("$2,000,000", styles['TableValue']), 
         Paragraph("Amounts above $2M require facultative reinsurance", styles['TableValue'])],
        [Paragraph("Deductible", styles['TableValue']), 
         Paragraph("None ($0.00)", styles['TableValue']), 
         Paragraph("Life insurance carries no deductible", styles['TableValue'])],
        [Paragraph("Premium Payment Modes", styles['TableValue']), 
         Paragraph("Annual, Semi-Annual, Quarterly, Monthly EFT", styles['TableValue']), 
         Paragraph("Modal factors: Semi 0.51, Qtr 0.26, Monthly 0.087", styles['TableValue'])],
    ]
    t = Table(table_data, colWidths=[150, 160, 190])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F1F5F9")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    # SECTION II - RISK CLASSES & RATING FACTORS
    story.append(Paragraph("SECTION II - RISK CLASSIFICATION & RATING FACTORS", styles['SectionHeading']))
    story.append(Paragraph("Clause 2.1: Underwriting Rate Classes", styles['ClauseHeading']))
    story.append(Paragraph(
        "Applicants are assigned to one of five distinct risk classes: (1) Preferred Plus Non-Tobacco, (2) Preferred Non-Tobacco, "
        "(3) Standard Non-Tobacco, (4) Preferred Tobacco, and (5) Standard Tobacco. Tobacco is defined as any nicotine or tobacco use "
        "in the preceding 36 months.",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Clause 2.2: Face Amount Bands & Band Pricing Discounts", styles['ClauseHeading']))
    story.append(Paragraph(
        "Mortality rate per $1,000 decreases across 3 size bands: Band 1 ($100,000 to $249,999 - Standard Rate), "
        "Band 2 ($250,000 to $999,999 - $0.15 per thousand discount), and Band 3 ($1,000,000 to $2,000,000 - $0.32 per thousand discount).",
        styles['ClauseBody']
    ))

    story.append(PageBreak()) # Page 2

    # SECTION III - ELIGIBILITY & MEDICAL UNDERWRITING
    story.append(Paragraph("SECTION III - UNDERWRITING REQUIREMENTS & ELIGIBILITY RULES", styles['SectionHeading']))
    story.append(Paragraph("Rule UW-LIFE-1: Paramedical Exam and Fluid Testing Requirements", styles['ClauseHeading']))
    story.append(Paragraph(
        "Automated underwriting with no exam is permitted for applicants aged 18-45 up to $500,000 face amount. "
        "A full paramedical examination, blood chemistry profile, resting ECG, and urinalysis are mandatory for: "
        "(a) all applicants aged 51 to 65 regardless of face amount; or (b) any face amount exceeding $500,000.",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Rule UW-LIFE-2: Build and Body Mass Index (BMI) Thresholds", styles['ClauseHeading']))
    story.append(Paragraph(
        "Preferred Plus Non-Tobacco requires a BMI between 19.0 and 28.5. Preferred Non-Tobacco requires a BMI between 18.5 and 31.0. "
        "Applicants with a BMI exceeding 38.0 are declined.",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Rule UW-LIFE-3: Major Medical History Ineligibility", styles['ClauseHeading']))
    story.append(Paragraph(
        "Any diagnosis, treatment, or clinical history of coronary artery disease, myocardial infarction, stroke, transient ischemic attack (TIA), "
        "or internal malignant cancer within 10 years of application constitutes an automatic decline.",
        styles['ClauseBody']
    ))

    story.append(PageBreak()) # Page 3

    # SECTION IV - EXCLUSIONS & INCONTESTABILITY
    story.append(Paragraph("SECTION IV - STATUTORY EXCLUSIONS & CONDITIONS", styles['SectionHeading']))
    story.append(Paragraph("Clause 4.1: Statutory Suicide Exclusion (Illinois Insurance Code)", styles['ClauseHeading']))
    story.append(Paragraph(
        "If the insured dies by suicide, sane or insane, within 2 years from the policy issue date, the death benefit is limited "
        "strictly to the sum of premiums paid, less any policy indebtedness. Full face amount is payable after 2 years.",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Clause 4.2: Incontestability Clause", styles['ClauseHeading']))
    story.append(Paragraph(
        "Except for non-payment of premium, this policy becomes incontestable after it has been in force during the lifetime "
        "of the insured for 2 years from the issue date. Material misrepresentation during contestability permits policy rescission.",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Clause 4.3: Aviation and War Exclusion", styles['ClauseHeading']))
    story.append(Paragraph(
        "Death resulting from piloting non-commercial aircraft or military operations during declared or undeclared warfare is excluded, "
        "refunding only the policy reserve.",
        styles['ClauseBody']
    ))

    # SECTION V - RIDERS & ENDORSEMENTS
    story.append(Paragraph("SECTION V - OPTIONAL RIDERS & ENDORSEMENTS", styles['SectionHeading']))
    story.append(Paragraph("Rider R-LIFE-01: Accelerated Death Benefit for Terminal Illness", styles['ClauseHeading']))
    story.append(Paragraph(
        "Enables the policyholder to accelerate up to 75% of the base face amount (maximum $500,000) upon certified clinical diagnosis "
        "of a terminal illness with life expectancy of 12 months or less. Included automatically at no initial premium surcharge.",
        styles['ClauseBody']
    ))

    story.append(Paragraph("Rider R-LIFE-02: Total Disability Waiver of Premium", styles['ClauseHeading']))
    story.append(Paragraph(
        "Waives all future premium payments if the insured becomes totally and permanently disabled prior to age 60, "
        "following a 6-month continuous elimination period. Additional modal premium charge applies based on attained age.",
        styles['ClauseBody']
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated Term Life Spec PDF: {output_path}")


def main():
    """Generates all 3 sample documents in the samples/ folder."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(base_dir, exist_ok=True)
    
    auto_pdf = os.path.join(base_dir, "sample_auto_policy.pdf")
    home_pdf = os.path.join(base_dir, "sample_homeowners_policy.pdf")
    life_pdf = os.path.join(base_dir, "sample_term_life_spec.pdf")
    
    generate_auto_policy_pdf(auto_pdf)
    generate_homeowners_policy_pdf(home_pdf)
    generate_term_life_spec_pdf(life_pdf)
    print("All 3 synthetic insurance product PDFs successfully generated in samples/")


if __name__ == "__main__":
    main()
