### ESP Automation Request

---

#### Request (Choose one):

- [x] Automation Script
- [ ] Auto-Remediation Function


#### Type (Choose one):

- [x] New Project
- [ ] Feature Enhancement
- [ ] Bug Report
 
 
**Required By (mm/dd/yyyy):**
07/06/2017


**Requested By (email addresses separated by commas):**
john_doe@evident.io

---

#### Product Area:
Suppressions


#### Description (If the current behavior is a bug, please provide the steps to reproduce):
Provide customers with a csv to audit the active suppressions configured in an ESP organization.


#### Use Case (What is the expected behavior?):
The need to audit suppressions includes, but is not limited to, the following questions:

1. What external accounts have suppressions enabled, who did it, when, and what are those suppressions for?
2. What regions are suppressed and for what external accounts?
3. What resources are suppressed and for what region and external account?
4. What signatures are suppressed and for what external account and what region?


#### Technical Requirements:
Suppressions are based on the following criteria:

* external_accounts
* regions
* signatures
* custom_signatures
* resource
* status


#### Supporting Image / Examples:
N/A


#### Additional Comments:
N/A
