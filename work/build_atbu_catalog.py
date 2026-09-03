"""Build ATBU's catalogue from its official faculty and recruitment directories."""

import json
from pathlib import Path


OUTPUT = Path(__file__).parents[1] / "data" / "atbu_academic_catalog.json"
SOURCES = [
    "https://atbu.edu.ng/?p=services",
    "https://recruitment.atbu.edu.ng/adverts",
    "https://atbu.edu.ng/wp-content/uploads/2025/05/Student_Handbook_Finally_23-3.pdf",
]

FACULTIES = {
    "Faculty of Agriculture and Agricultural Technology": [
        "Agricultural Economics", "Agricultural Extension and Rural Development",
        "Animal Production", "Crop Production", "Soil Science",
    ],
    "Faculty of Allied Medical Sciences": ["Nursing Science", "Public Health"],
    "Faculty of Basic Clinical Sciences": [
        "Chemical Pathology", "Haematology", "Histopathology", "Medical Microbiology",
        "Clinical Pharmacology",
    ],
    "Faculty of Basic Medical Sciences": ["Human Anatomy", "Medical Biochemistry", "Human Physiology"],
    "Faculty of Clinical Sciences": [
        "Internal Medicine", "Surgery", "Paediatrics", "Obstetrics and Gynaecology",
        "Community Medicine", "Ophthalmology", "Anaesthesia", "Otorhinolaryngology",
        "Orthopaedics", "Radiology", "Psychiatry",
    ],
    "Faculty of Computing": [
        "Computer Science", "Software Engineering", "Cyber Security", "Artificial Intelligence",
        "Information Technology", "Information Systems",
    ],
    "Faculty of Engineering and Engineering Technology": [
        "Agricultural and Bio-Resource Engineering", "Automobile Engineering", "Chemical Engineering",
        "Civil Engineering", "Computer and Communications Engineering", "Electrical and Electronics Engineering",
        "Mechanical and Production Engineering", "Mechatronics and Systems Engineering", "Petroleum Engineering",
    ],
    "Faculty of Environmental Technology": [
        "Architecture", "Building", "Environmental Management Technology", "Estate Management and Valuation",
        "Industrial Design", "Quantity Surveying", "Surveying and Geoinformatics", "Urban and Regional Planning",
    ],
    "Faculty of Science": ["Biochemistry", "Microbiology", "Botany", "Zoology", "Mathematics", "Chemistry", "Physics"],
    "Faculty of Veterinary Medicine": [
        "Veterinary Anatomy", "Veterinary Physiology and Biochemistry", "Veterinary Pharmacology and Toxicology",
        "Theriogenology and Production", "Veterinary Microbiology", "Veterinary Parasitology and Entomology",
        "Veterinary Pathology",
    ],
}

SHARED = {
    "Faculty of Basic Clinical Sciences": ["MBBS"],
    "Faculty of Clinical Sciences": ["MBBS"],
    "Faculty of Veterinary Medicine": ["DVM"],
}


def degree_name(faculty, department):
    if faculty in SHARED:
        return SHARED[faculty]
    if department == "Nursing Science":
        return ["B.NSc Nursing Science"]
    if department == "Public Health":
        return ["B.Sc Public Health"]
    if faculty == "Faculty of Engineering and Engineering Technology":
        return [f"B.Eng {department}"]
    if department == "Architecture":
        return ["B.Tech Architecture"]
    return [f"B.Tech {department}"]


catalogue = {
    "university": "Abubakar Tafawa Balewa University, Bauchi",
    "verified": "2026-09-03",
    "sources": SOURCES,
    "faculties": [
        {
            "name": faculty,
            "departments": [
                {"name": department, "programmes": degree_name(faculty, department)}
                for department in departments
            ],
        }
        for faculty, departments in FACULTIES.items()
    ],
}

OUTPUT.write_text(json.dumps(catalogue, indent=2, ensure_ascii=False) + "\n")
print(
    f"Wrote {OUTPUT}: {len(catalogue['faculties'])} faculties, "
    f"{sum(len(f['departments']) for f in catalogue['faculties'])} departments"
)
