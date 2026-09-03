"""Build ABU's institution catalogue from its official programme directory."""

import html
import json
import re
import urllib.request
from collections import defaultdict
from pathlib import Path


SOURCE = "https://programmes.abu.edu.ng/programmes_list.php?tab=6&page=list"
OUTPUT = Path(__file__).parents[1] / "data" / "abu_academic_catalog.json"

# The programme directory identifies the department responsible for each active
# undergraduate award.  The current student handbook is the authority for the
# complete academic-unit structure, including service/clinical departments that
# do not own a separate undergraduate award.
HANDBOOK_DEPARTMENTS = {
    "Faculty of Administration": ["Public Administration", "Local Government and Development Studies"],
    "ABU Business School": ["Accounting", "Business Administration", "Economics", "Banking and Finance", "Marketing", "Actuarial Science and Insurance"],
    "Faculty of Agriculture": ["Agricultural Economics", "Agricultural Extension and Rural Development", "Agronomy", "Animal Science", "Crop Protection", "Fisheries and Aquaculture", "Forestry and Wildlife Management", "Plant Science", "Soil Science"],
    "Faculty of Arts": ["Archaeology", "Theatre and Performing Arts", "English", "French", "History", "African Languages and Cultures", "Arabic"],
    "Faculty of Education": ["Arts and Social Studies Education", "Educational Psychology and Counselling", "Educational Foundations and Curriculum", "Science Education", "Library and Information Science", "Human Kinetics and Health Education", "Vocational and Technical Education", "Home Economics"],
    "Faculty of Engineering": ["Agricultural Engineering", "Chemical Engineering", "Civil Engineering", "Electrical Engineering", "Mechanical Engineering", "Metallurgical and Materials Engineering", "Water Resources and Environmental Engineering", "Polymer and Textile Engineering", "Computer Engineering", "Electronics and Telecommunications Engineering", "Automotive Engineering", "Mechatronics Engineering"],
    "Faculty of Environmental Design": ["Architecture", "Building", "Fine Arts", "Industrial Design", "Geomatics", "Quantity Surveying", "Urban and Regional Planning"],
    "Faculty of Law": ["Commercial Law", "Islamic Law", "Private Law", "Public Law"],
    "Faculty of Clinical Sciences": ["Anaesthesia", "Community Medicine", "Dental Surgery", "Medicine", "Obstetrics and Gynaecology", "Ophthalmology", "Paediatrics", "Psychiatry", "Surgery", "Traumatic and Orthopaedic Surgery"],
    "Faculty of Basic Medical Sciences": ["Anatomy", "Human Physiology"],
    "Faculty of Basic Clinical Sciences": ["Chemical Pathology", "Haematology and Blood Transfusion", "Medical Microbiology", "Pathology"],
    "Faculty of Allied Health Sciences": ["Nursing Sciences", "Medical Laboratory Sciences", "Medical Radiography", "Medical Biology", "Clinical Pharmacology"],
    "Faculty of Pharmaceutical Sciences": ["Pharmaceutical and Medicinal Chemistry", "Pharmacognosy and Drug Development", "Pharmacology and Clinical Pharmacy", "Pharmaceutics and Pharmaceutical Microbiology"],
    "Faculty of Life Sciences": ["Biochemistry", "Biological Sciences", "Microbiology"],
    "Faculty of Physical Sciences": ["Chemistry", "Geography", "Geology", "Mathematics", "Computer Science", "Physics", "Statistics"],
    "Faculty of Social Sciences": ["Economics", "Mass Communication", "Political Science", "Sociology"],
    "Faculty of Veterinary Medicine": ["Veterinary Anatomy", "Veterinary Parasitology and Entomology", "Veterinary Pathology and Microbiology", "Veterinary Physiology and Pharmacology", "Veterinary Public Health and Preventive Medicine", "Veterinary Surgery and Medicine", "Veterinary Microbiology", "Veterinary Surgery and Radiology"],
}

DEPARTMENT_ALIASES = {
    "Business Management": "Business Administration",
    "Insurance": "Actuarial Science and Insurance",
    "Fisheries": "Fisheries and Aquaculture",
    "Forestry and Wildlife": "Forestry and Wildlife Management",
    "Arts and Social Science Education": "Arts and Social Studies Education",
    "Educational Foundation and Curriculum": "Educational Foundations and Curriculum",
    "Physical and Health Education": "Human Kinetics and Health Education",
    "ELECTRONICS AND TELECOMMUNICATIONS ENGINEERING": "Electronics and Telecommunications Engineering",
    "Geography and Environmental Management": "Geography",
    "Medical Laboratory Science": "Medical Laboratory Sciences",
    "Nursing Science": "Nursing Sciences",
    "Human Anatomy": "Anatomy",
    "Pharmacy": "Pharmaceutics and Pharmaceutical Microbiology",
    "Civil Law": "Private Law",
    "Veterinary Medicine": "Veterinary Surgery and Medicine",
}

SHARED_PROGRAMMES = {
    "Faculty of Law": ["LL.B"],
    "Faculty of Clinical Sciences": ["MBBS"],
    "Faculty of Basic Clinical Sciences": ["MBBS"],
    "Faculty of Pharmaceutical Sciences": ["B. Pharmacy"],
    "Faculty of Veterinary Medicine": ["DVM"],
}


def clean(value):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", value)).split())


def faculty_name(value):
    value = clean(value)
    if value == "ABU Business School":
        return value
    return value if value.startswith("Faculty of ") else f"Faculty of {value}"


records = []
for page in range(1, 7):
    url = f"{SOURCE}&goto={page}"
    request = urllib.request.Request(url, headers={"User-Agent": "Quizzle academic catalogue verifier"})
    markup = urllib.request.urlopen(request, timeout=30).read().decode("utf-8", "replace")
    rows = re.findall(r'<tr\s+id="gridRow\d+".*?</tr>', markup, re.S)
    for row in rows:
        fields = {}
        for field in ("name", "delivery_mode", "faculty", "department_id"):
            match = re.search(rf'id="edit\d+_{field}"\s*>(.*?)</span>', row, re.S)
            fields[field] = clean(match.group(1)) if match else ""
        if all(fields.values()):
            records.append(fields)

hierarchy = defaultdict(lambda: defaultdict(set))
for item in records:
    faculty = faculty_name(item["faculty"])
    department = DEPARTMENT_ALIASES.get(item["department_id"], item["department_id"])
    if department in HANDBOOK_DEPARTMENTS.get(faculty, []):
        hierarchy[faculty][department].add(item["name"])

for faculty, departments in HANDBOOK_DEPARTMENTS.items():
    for department in departments:
        hierarchy[faculty][department].update(SHARED_PROGRAMMES.get(faculty, []))

catalogue = {
    "university": "Ahmadu Bello University, Zaria",
    "verified": "2026-09-03",
    "sources": [
        "https://abu.edu.ng/wp-content/uploads/2026/06/ABU-Student-Handbook-for-the-2025-2026-Session.pdf",
        SOURCE,
    ],
    "faculties": [
        {
            "name": faculty,
            "departments": [
                {"name": department, "programmes": sorted(programmes)}
                for department, programmes in sorted(departments.items())
            ],
        }
        for faculty, departments in sorted(hierarchy.items())
    ],
}

OUTPUT.write_text(json.dumps(catalogue, indent=2, ensure_ascii=False) + "\n")
print(
    f"Wrote {OUTPUT}: {len(catalogue['faculties'])} faculties, "
    f"{sum(len(f['departments']) for f in catalogue['faculties'])} departments, "
    f"{sum(len(d['programmes']) for f in catalogue['faculties'] for d in f['departments'])} programmes"
)
