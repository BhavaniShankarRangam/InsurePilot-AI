"""Synthetic policy documents for demo mode. Fictional carriers; not real policy language."""

AUTO_POLICY = {
    1: """DECLARATIONS PAGE
Northstar Mutual Personal Auto Policy. Named insured: Alex Morgan. Policy period: 12 months.
Insured vehicle: 2022 Toyota RAV4 XLE. Garaging location: Austin, Texas.
Coverages shown with a limit apply. Coverages without a limit are not provided.
Bodily injury liability $100,000 each person / $300,000 each accident. Property damage liability $100,000 each accident.
Medical payments $5,000 each person. Uninsured motorist bodily injury $100,000 / $300,000.
Collision deductible $1,000. Comprehensive deductible $500. Rental reimbursement $40 per day up to $1,200.
Roadside assistance included. Total 12-month premium $1,916.00.""",
    6: """SECTION 1 — LIABILITY COVERAGE
We will pay damages for bodily injury or property damage for which any insured becomes legally responsible because of an auto accident.
We will settle or defend, as we consider appropriate, any claim or suit asking for these damages.
Our duty to settle or defend ends when the limit of liability for this coverage has been exhausted by payment of judgments or settlements.
The limit of liability shown in the Declarations for each person is our maximum limit for all damages arising out of bodily injury sustained by any one person in any one auto accident.""",
    10: """SECTION 2 — MEDICAL PAYMENTS COVERAGE
We will pay reasonable expenses incurred for necessary medical and funeral services because of bodily injury caused by accident and sustained by an insured.
We will pay only those expenses incurred for services rendered within 3 years from the date of the accident.
Medical payments coverage applies regardless of who is at fault for the accident.""",
    12: """SECTION 3 — UNINSURED MOTORIST COVERAGE
We will pay compensatory damages which an insured is legally entitled to recover from the owner or operator of an uninsured motor vehicle because of bodily injury.
An uninsured motor vehicle includes a hit-and-run vehicle whose operator or owner cannot be identified.
You must notify the police within 24 hours of a hit-and-run accident.""",
    18: """SECTION 4 — COLLISION COVERAGE
We will pay for direct and accidental loss to your covered auto caused by collision with another object or by overturn, minus the collision deductible shown in the Declarations.
Your collision deductible is $1,000 per occurrence. If the other driver is found legally responsible, we may recover payment from that driver's insurer and refund your deductible in proportion to the amount recovered.
Our limit of liability for loss is the lesser of the actual cash value of the damaged property or the amount necessary to repair or replace it with property of like kind and quality.
Filing a collision claim where you are at fault may affect your premium at renewal.""",
    20: """SECTION 5 — COMPREHENSIVE COVERAGE
We will pay for direct and accidental loss to your covered auto not caused by collision, minus the comprehensive deductible of $500.
Loss caused by the following is considered other than collision: missiles or falling objects, fire, theft, explosion, earthquake, windstorm, hail, water, flood, vandalism, riot, contact with a bird or animal, and breakage of glass.
Glass repair is covered with no deductible when the glass is repaired rather than replaced.""",
    23: """SECTION 6 — RENTAL REIMBURSEMENT
We will pay up to $40 per day, to a maximum of $1,200, for transportation expenses when your covered auto is withdrawn from use due to a loss covered under Collision or Comprehensive.
Payment begins when the auto cannot be driven or is left at a repair facility and ends when the auto is repaired or replaced.""",
    24: """SECTION 7 — ROADSIDE ASSISTANCE
We will pay for towing up to 15 miles, battery jump-start, flat-tire change, lockout service, and fuel delivery (cost of fuel not included).
Call the number on your insurance card to request roadside service. Limit of 4 service calls per policy period.""",
    27: """EXCLUSIONS
We do not provide coverage for loss to your covered auto due to wear and tear, freezing, mechanical or electrical breakdown, or road damage to tires.
We do not provide coverage for any vehicle while used to carry persons or property for a fee, including ridesharing, unless the Rideshare Endorsement is attached.
We do not provide coverage for intentional damage caused by an insured.
We do not provide coverage for custom equipment exceeding $1,000 unless scheduled on the policy.""",
    29: """CONDITIONS — DUTIES AFTER AN ACCIDENT OR LOSS
You must give us prompt notice of any accident or loss, including how, when and where it happened.
You must submit proof of loss when required, permit us to inspect and appraise the damaged property before repair, and cooperate in the investigation.
Photographs of damage and a copy of any police report should be provided within 30 days of the loss.""",
    31: """RENEWAL NOTICE — PREMIUM CHANGE SUMMARY
Your policy renews with a new 12-month premium of $1,916.00, compared with your prior premium of $1,610.00.
Factors applied at this renewal: an at-fault collision claim within the last 36 months (surcharge applied); the multi-policy discount was removed because the linked renters policy ended; base rates in your area changed.
Please review your coverages before the renewal date. You may contact us to discuss available discounts, including safe-driver and paperless discounts.""",
}

HOME_POLICY = {
    1: """DECLARATIONS PAGE
Harborline Insurance Homeowners Policy HO-3. Named insured: Alex Morgan. Residence premises: Austin, Texas.
Coverage A Dwelling $320,000. Coverage B Other Structures $32,000. Coverage C Personal Property $160,000.
Coverage D Loss of Use $64,000. Coverage E Personal Liability $300,000. Coverage F Medical Payments to Others $5,000.
All-peril deductible $2,500. Wind/hail deductible 1% of Coverage A. Endorsements: HO-WB Water Backup and Sump Discharge ($10,000).
Annual premium $2,184.00.""",
    5: """SECTION I — COVERAGE A DWELLING
We cover the dwelling on the residence premises, including structures attached to the dwelling, and materials and supplies on the premises used to construct, alter or repair the dwelling.
Loss to the dwelling is settled at replacement cost without deduction for depreciation, up to the Coverage A limit.
If the Coverage A limit is less than 80% of the full replacement cost of the dwelling at the time of loss, we will pay the larger of the actual cash value or a proportion of the replacement cost.""",
    7: """SECTION I — COVERAGE C PERSONAL PROPERTY
We cover personal property owned or used by an insured while it is anywhere in the world.
Special limits apply: $1,500 for theft of jewelry and watches, $2,500 for theft of firearms, $200 for money and bank notes.
Personal property is settled at actual cash value unless the Personal Property Replacement Cost endorsement is attached.""",
    9: """SECTION I — COVERAGE D LOSS OF USE
If a loss covered under Section I makes the residence premises not fit to live in, we cover additional living expenses — any necessary increase in living expenses incurred so that your household can maintain its normal standard of living.""",
    14: """SECTION I — EXCLUSIONS
Water. We do not insure for loss caused by water damage, meaning: flood, surface water, waves, tidal water or overflow of a body of water; water which backs up through sewers or drains or which overflows or is discharged from a sump, sump pump or related equipment; or water below the surface of the ground.
This exclusion applies regardless of any other cause or event contributing concurrently or in any sequence to the loss.
This exclusion may be modified by an endorsement attached to this policy.
Wear and tear, marring, deterioration, mold, fungus or wet rot, and continuous or repeated seepage of water over a period of 14 days or more are also excluded.""",
    16: """SECTION I — CONDITIONS — DUTIES AFTER LOSS
In case of a loss, you must give prompt notice to us, protect the property from further damage, make reasonable repairs to protect the property, and keep records of repair expenses.
You must prepare an inventory of damaged personal property and submit a signed, sworn proof of loss within 60 days after our request.""",
    18: """SECTION II — COVERAGE E PERSONAL LIABILITY
If a claim is made or a suit is brought against an insured for damages because of bodily injury or property damage caused by an occurrence to which this coverage applies, we will pay up to our limit of liability and provide a defense at our expense.""",
    31: """ENDORSEMENT HO-WB — WATER BACKUP AND SUMP DISCHARGE OR OVERFLOW
We will pay up to $10,000 for direct physical loss caused by water which backs up through sewers or drains, or which overflows or is discharged from a sump, sump pump or related equipment, even if the overflow results from mechanical breakdown.
This coverage does not apply to loss caused by flood or surface water, or to loss caused by your negligence in maintaining the sump pump.
A deductible of $1,000 applies to each loss under this endorsement.
This endorsement modifies the Water exclusion in Section I only to the extent described above.""",
    33: """APPEALS AND DISPUTE RESOLUTION
If you disagree with our claim decision, you may request reconsideration in writing within 60 days of the decision letter. Include any additional documentation, such as a plumber's or contractor's report on the cause of loss.
If we and you fail to agree on the amount of loss, either may demand an appraisal.""",
}

HEALTH_POLICY = {
    1: """SUMMARY OF BENEFITS AND COVERAGE
Bluepeak Health Choice PPO 2500. Coverage period: calendar year. Coverage for: individual.
Overall deductible: $2,500 individual in-network; $5,000 out-of-network.
Out-of-pocket maximum: $6,500 individual in-network; $13,000 out-of-network.
Primary care visit: $30 copay. Specialist visit: $60 copay. Urgent care: $75 copay. Emergency room: $350 copay then 20% coinsurance.
Diagnostic imaging (CT, PET, MRI): 20% coinsurance after deductible in-network; 40% out-of-network. Preauthorization required.""",
    8: """SECTION 3 — HOW YOUR COST SHARING WORKS
Deductible: the amount you pay for covered services each plan year before the plan begins to pay, except services with a copay.
Coinsurance: your share of the allowed amount after you meet your deductible. For in-network services your coinsurance is 20%.
Allowed amount: the maximum amount the plan pays for a covered service. In-network providers agree to accept the allowed amount and may not bill you for the difference.
Out-of-pocket maximum: once you reach this amount in a plan year, the plan pays 100% of covered in-network services.""",
    14: """SECTION 5 — PROVIDER NETWORK
The Bluepeak Choice network includes participating hospitals, physicians and imaging centers. Use the online directory or call Member Services to confirm a provider's participation before you receive care.
A hospital may participate in the network while individual physicians practicing there (such as radiologists or anesthesiologists) do not. Ask each provider whether they are in-network.
Out-of-network providers may bill you for the difference between their charge and the allowed amount (balance billing), except where prohibited by law.""",
    22: """SECTION 7 — PRIOR AUTHORIZATION
Prior authorization is required for: advanced imaging (MRI, CT, PET), inpatient admissions, outpatient surgery, and specialty drugs.
Your provider must submit a request with clinical documentation, including relevant notes, prior treatment tried, and the reason the service is needed.
Standard requests are decided within 15 calendar days; urgent requests within 72 hours.
If prior authorization is not obtained, the claim may be denied or reduced. Authorization does not guarantee payment; benefits depend on eligibility at the time of service.""",
    30: """SECTION 9 — CLAIMS AND APPEALS
You will receive an Explanation of Benefits (EOB) after each claim is processed. The EOB is not a bill.
If a claim is denied, you may file an internal appeal within 180 days of the denial notice. You may request copies of documents relevant to your claim free of charge.
If the internal appeal is denied, you may request an external review by an independent review organization.""",
}

LIFE_POLICY = {
    1: """POLICY SCHEDULE
Evergreen Life Term 20. Insured: Alex Morgan. Face amount (death benefit): $750,000. Level premium period: 20 years.
Annual premium: $612.00. Policy owner: Alex Morgan.
Primary beneficiary: Jordan Morgan (spouse), 100%. Contingent beneficiary: none designated.""",
    4: """SECTION 2 — BENEFICIARIES
The primary beneficiary receives the death benefit. If no primary beneficiary survives the insured, the contingent beneficiary receives the death benefit.
If no beneficiary survives the insured, the death benefit is paid to the owner or the owner's estate, which may delay payment and subject proceeds to probate.
You may change beneficiaries at any time by written request.""",
    7: """SECTION 4 — CONVERSION PRIVILEGE
You may convert this policy to a permanent life insurance policy without evidence of insurability before the policy anniversary nearest the insured's age 70 or the end of the level premium period, whichever comes first.""",
}

PET_POLICY = {
    1: """POLICY DECLARATIONS
Pawsure Accident & Illness Plan. Pet: Miso (dog, mixed breed, age 4). Annual deductible $250. Reimbursement 80%. Annual limit $10,000.
Monthly premium $38.00. Waiting periods: 2 days for accidents, 14 days for illnesses.""",
    3: """EXCLUSIONS
Pre-existing conditions, routine wellness care, grooming, and breeding costs are not covered.""",
}
