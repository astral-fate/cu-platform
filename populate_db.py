import logging
from run import app, db
from models import Program, Course, ProgramCourse

# Configure basic logging to see the progress
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- COMPLETE PROGRAM DATA STRUCTURE WITH ARABIC COURSE TITLES ---
PROGRAM_DATA = [
    # 1. Project Management
    {
        "name_en": "Project Management", "name_ar": "إدارة المشروعات", "type": "Professional",
        "degrees": {
            "Diploma": {
                "desc_ar": "دبلوم مهني في إدارة المشروعات.",
                "courses": {
                    1: [
                        {"code": "PM101", "title": "أساسيات إدارة المشروعات", "credits": 3, "semester": 1, "description": "مقدمة شاملة لأهم مفاهيم ومبادئ إدارة المشروعات."},
                        {"code": "PM102", "title": "تحليل البيانات", "credits": 3, "semester": 1},
                        {"code": "PM103", "title": "إدارة مخاطر المشروع", "credits": 3, "semester": 2, "description": "تحديد وإدارة مخاطر المشروع."},
                        {"code": "PM104", "title": "الهيكل التنظيمي والاتصال", "credits": 3},
                        {"code": "PM105", "title": "اتخاذ القرار", "credits": 3},
                    ],
                    2: [
                        {"code": "PM201", "title": "الميزانية والتكلفة", "credits": 3},
                        {"code": "PM202", "title": "إدارة الأزمات والمخاطر", "credits": 3},
                        {"code": "PM203", "title": "مراقبة المشروع", "credits": 3},
                        {"code": "PM204", "title": "إدارة الجودة الشاملة", "credits": 3},
                        {"code": "PM205", "title": "مشروع", "credits": 3},
                    ]
                }
            },
            "Master": {
                "desc_ar": "ماجستير مهني في إدارة المشروعات.",
                "courses": {
                    1: [
                        {"code": "PM501", "title": "مبادئ ومنهجيات البحث العلمي", "credits": 3},
                        {"code": "PM502", "title": "دراسات الجدوى للمشروعات", "credits": 3},
                        {"code": "PM503", "title": "موضوعات مختارة في إدارة المشروعات", "credits": 3},
                    ],
                    2: [
                        {"code": "PM601", "title": "تحليل التكلفة والعائد وتقييم المشروعات", "credits": 3},
                        {"code": "PM602", "title": "إدارة المشروعات في الممارسة العملية", "credits": 3},
                        {"code": "PM603", "title": "برامج إدارة المشروعات", "credits": 3},
                        {"code": "PM604", "title": "مشروع", "credits": 6},
                    ]
                }
            },
            "PhD": {
                "desc_ar": "دكتوراه في إدارة المشروعات.",
                "courses": {
                    1: [
                        {"code": "PM901", "title": "إدارة السلوك التنظيمي", "credits": 3},
                        {"code": "PM902", "title": "الموارد البشرية الاستراتيجية", "credits": 3},
                        {"code": "PM903", "title": "تقييم مشروعات التنمية", "credits": 3},
                    ],
                    2: [
                        {"code": "PM951", "title": "تحليل القيمة للمشروعات الهندسية", "credits": 3},
                        {"code": "PM952", "title": "إدارة المشروعات المتعددة", "credits": 3},
                        {"code": "PM953", "title": "قراءات فردية موجهة (موضوعات متقدمة)", "credits": 3},
                    ]
                }
            }
        }
    },
    # 2. Operations Research and Decision Support
    {
        "name_en": "Operations Research and Decision Support", "name_ar": "بحوث العمليات ودعم القرار", "type": "Professional",
        "degrees": {
            "Diploma": {
                "desc_ar": "دبلوم في بحوث العمليات ودعم القرار.",
                "courses": {
                    1: [
                        {"code": "OR101", "title": "نماذج بحوث العمليات وتطبيقاتها", "credits": 3},
                        {"code": "OR102", "title": "نظم دعم القرار", "credits": 3},
                        {"code": "OR103", "title": "تحليل إحصائي للأعمال", "credits": 3},
                        {"code": "OR104", "title": "إدارة المشروعات والشبكات", "credits": 3},
                        {"code": "OR105", "title": "إدارة المخزون", "credits": 3},
                    ],
                    2: [
                        {"code": "OR201", "title": "إدارة العمليات", "credits": 3},
                        {"code": "OR202", "title": "النمذجة والمحاكاة", "credits": 3},
                        {"code": "OR203", "title": "مراقبة الجودة", "credits": 3},
                        {"code": "OR204", "title": "برمجيات بحوث العمليات", "credits": 3},
                        {"code": "OR205", "title": "مشروع", "credits": 3},
                    ]
                }
            },
            "Master": {
                "desc_ar": "ماجستير في بحوث العمليات ودعم القرار.",
                 "courses": {
                    1: [
                        {"code": "OR501", "title": "مبادئ ومنهجيات البحث العلمي", "credits": 3},
                        {"code": "OR502", "title": "موضوعات متقدمة في اتخاذ القرار", "credits": 3},
                        {"code": "OR503", "title": "التنبؤ", "credits": 3},
                    ],
                    2: [
                        {"code": "OR601", "title": "الجدولة", "credits": 3},
                        {"code": "OR602", "title": "إدارة سلسلة الإمداد", "credits": 3},
                        {"code": "OR603", "title": "برمجيات بحوث العمليات المتقدمة", "credits": 3},
                        {"code": "OR604", "title": "مشروع", "credits": 6},
                    ]
                }
            },
            "PhD": {
                "desc_ar": "دكتوراه في بحوث العمليات ودعم القرار.",
                "courses": {
                    1: [
                        {"code": "OR901", "title": "موضوعات متقدمة في نظم دعم القرار", "credits": 3},
                        {"code": "OR902", "title": "اتخاذ القرار متعدد المعايير", "credits": 3},
                        {"code": "OR903", "title": "النماذج الاحتمالية", "credits": 3},
                    ],
                    2: [
                        {"code": "OR951", "title": "تطبيقات نظرية الألعاب", "credits": 3},
                        {"code": "OR952", "title": "موضوعات متقدمة في بحوث العمليات", "credits": 3},
                        {"code": "OR953", "title": "قراءات فردية موجهة (موضوعات متقدمة)", "credits": 3},
                    ]
                }
            }
        }
    },
    # 3. Supply Chain and Operations Management
    {
        "name_en": "Supply Chain and Operations Management", "name_ar": "سلسلة الإمداد وإدارة العمليات", "type": "Professional",
        "degrees": {
            "Diploma": {
                "desc_ar": "دبلوم في سلسلة الإمداد وإدارة العمليات.",
                "courses": {
                    1: [
                        {"code": "SC101", "title": "إدارة المشروعات: أدوات وتقنيات", "credits": 3},
                        {"code": "SC102", "title": "أدوات التحليل الكمي في اتخاذ القرار", "credits": 3},
                        {"code": "SC103", "title": "إدارة العمليات", "credits": 3},
                        {"code": "SC104", "title": "برمجيات إدارة العمليات", "credits": 3},
                        {"code": "SC105", "title": "إدارة سلسلة الإمداد", "credits": 3},
                    ],
                    2: [
                        {"code": "SC201", "title": "تحليل إحصائي للأعمال", "credits": 3},
                        {"code": "SC202", "title": "نظم المعلومات في سلسلة الإمداد", "credits": 3},
                        {"code": "SC203", "title": "إدارة الإنتاج", "credits": 3},
                        {"code": "SC204", "title": "إدارة الجودة", "credits": 3},
                        {"code": "SC205", "title": "مشروع", "credits": 3},
                    ]
                }
            },
            "Master": {
                "desc_ar": "ماجستير في سلسلة الإمداد وإدارة العمليات.",
                "courses": {
                    1: [
                        {"code": "SC501", "title": "مبادئ ومنهجيات البحث العلمي", "credits": 3},
                        {"code": "SC502", "title": "النمذجة والمحاكاة", "credits": 3},
                        {"code": "SC503", "title": "تحليل وتقييم المخاطر", "credits": 3},
                    ],
                    2: [
                        {"code": "SC601", "title": "الجدولة", "credits": 3},
                        {"code": "SC602", "title": "موضوعات متقدمة في إدارة العمليات", "credits": 3},
                        {"code": "SC603", "title": "برمجيات إدارة العمليات", "credits": 3},
                        {"code": "SC604", "title": "مشروع", "credits": 6},
                    ]
                }
            },
            "PhD": {
                "desc_ar": "دكتوراه في سلسلة الإمداد وإدارة العمليات.",
                "courses": {
                    1: [
                        {"code": "SC901", "title": "تخطيط المصانع والمواقع", "credits": 3},
                        {"code": "SC902", "title": "نظم العمليات اللينة", "credits": 3},
                        {"code": "SC903", "title": "تخطيط الإنتاج ومتطلبات المواد", "credits": 3},
                    ],
                    2: [
                        {"code": "SC951", "title": "التخطيط الكلي واستراتيجية العمليات", "credits": 3},
                        {"code": "SC952", "title": "الصيانة والموثوقية", "credits": 3},
                        {"code": "SC953", "title": "قراءات فردية موجهة (موضوعات متقدمة)", "credits": 3},
                    ]
                }
            }
        }
    },
    # 4. Web Design
    {
        "name_en": "Web Design", "name_ar": "تصميم المواقع", "type": "Professional",
        "degrees": {
            "Diploma": {
                "desc_ar": "دبلوم في تصميم المواقع.",
                 "courses": {
                    1: [
                        {"code": "WD101", "title": "مقدمة في علوم الحاسب", "credits": 3},
                        {"code": "WD102", "title": "قواعد بيانات SQL Server", "credits": 3},
                        {"code": "WD103", "title": "HTML 5 و CSS 3", "credits": 3},
                        {"code": "WD104", "title": "فوتوشوب لتصميم الويب", "credits": 3},
                        {"code": "WD105", "title": "ASP.NET, JavaScript و jQuery", "credits": 3},
                    ],
                    2: [
                        {"code": "WD201", "title": "برمجة الويب باستخدام PHP", "credits": 3},
                        {"code": "WD202", "title": "Bootstrap لتصميم الويب المتجاوب", "credits": 3},
                        {"code": "WD203", "title": "تطوير الويب لمحركات البحث (SEO)", "credits": 3},
                        {"code": "WD204", "title": "البرمجة الشيئية", "credits": 3},
                        {"code": "WD205", "title": "مشروع", "credits": 3},
                    ]
                }
            },
            "Master": {
                "desc_ar": "ماجستير في تصميم المواقع.",
                "courses": {
                    1: [
                        {"code": "WD501", "title": "تصميم وإدارة المواقع المتقدمة", "credits": 3},
                        {"code": "WD502", "title": "أمان تطبيقات الويب", "credits": 3},
                        {"code": "WD503", "title": "تطوير تطبيقات الويب المتقدمة", "credits": 3},
                    ],
                    2: [
                        {"code": "WD601", "title": "نظم قواعد البيانات المتقدمة", "credits": 3},
                        {"code": "WD602", "title": "تقنيات وممارسات أجايل", "credits": 3},
                        {"code": "WD603", "title": "منهجية البحث", "credits": 3},
                        {"code": "WD604", "title": "مشروع", "credits": 6},
                    ]
                }
            },
            "PhD": {
                "desc_ar": "دكتوراه في تصميم المواقع.",
                "courses": {
                    1: [
                        {"code": "WD901", "title": "تطوير تطبيقات الموبايل", "credits": 3},
                        {"code": "WD902", "title": "مستجدات في إدارة الويب", "credits": 3},
                        {"code": "WD903", "title": "موضوعات مختارة في تكنولوجيا الويب", "credits": 3},
                    ],
                    2: [
                        {"code": "WD951", "title": "قراءات فردية موجهة (موضوعات متقدمة)", "credits": 3},
                        {"code": "WD952", "title": "دراسات موجهة في علوم الويب", "credits": 3},
                        {"code": "WD953", "title": "دراسات فردية تحت الإشراف (موضوعات متقدمة)", "credits": 3},
                    ]
                }
            }
        }
    },
    # 5. Software Engineering
    {
        "name_en": "Software Engineering", "name_ar": "هندسة البرمجيات", "type": "Professional",
        "degrees": {
            "Diploma": {
                "desc_ar": "دبلوم في هندسة البرمجيات.",
                "courses": {
                    1: [
                        {"code": "SE101_D", "title": "مبادئ نظم الحاسب والبرمجة", "credits": 3},
                        {"code": "SE102_D", "title": "نظم قواعد البيانات العلائقية", "credits": 3},
                        {"code": "SE103_D", "title": "عملية تطوير البرمجيات", "credits": 3},
                        {"code": "SE104_D", "title": "تصميم واجهة المستخدم", "credits": 3},
                        {"code": "SE105_D", "title": "تطوير البرمجيات الشيئية باستخدام UML", "credits": 3},
                    ],
                    2: [
                        {"code": "SE201_D", "title": "إدارة مشروعات البرمجيات", "credits": 3},
                        {"code": "SE202_D", "title": "تصميم وهيكلة الويب", "credits": 3},
                        {"code": "SE203_D", "title": "تطوير البرمجيات أجايل", "credits": 3},
                        {"code": "SE204_D", "title": "البرمجة على نطاق واسع", "credits": 3},
                        {"code": "SE205_D", "title": "مشروع", "credits": 3},
                    ]
                }
            },
            "Master": {
                "desc_ar": "ماجستير في هندسة البرمجيات.",
                "courses": {
                    1: [
                        {"code": "SE501_M", "title": "مبادئ ومنهجيات البحث العلمي", "credits": 3},
                        {"code": "SE502_M", "title": "ضمان جودة البرمجيات", "credits": 3},
                        {"code": "SE503_M", "title": "موضوعات متقدمة في قواعد البيانات", "credits": 3},
                    ],
                    2: [
                        {"code": "SE601_M", "title": "موضوعات متقدمة في نظم المعلومات", "credits": 3},
                        {"code": "SE602_M", "title": "أمن المعلومات", "credits": 3},
                        {"code": "SE603_M", "title": "تطوير البرمجيات أجايل المتقدم", "credits": 3},
                        {"code": "SE604_M", "title": "مشروع", "credits": 6},
                    ]
                }
            },
            "PhD": {
                "desc_ar": "دكتوراه في هندسة البرمجيات.",
                "courses": {
                    1: [
                        {"code": "SE901_P", "title": "موضوعات مختارة في هندسة البرمجيات", "credits": 3},
                        {"code": "SE902_P", "title": "موضوعات مختارة في نظم المعلومات", "credits": 3},
                        {"code": "SE903_P", "title": "موضوعات مختارة في تكنولوجيا المعلومات", "credits": 3},
                    ],
                    2: [
                        {"code": "SE951_P", "title": "تخزين البيانات", "credits": 3},
                        {"code": "SE952_P", "title": "تطوير حلول التجارة الإلكترونية", "credits": 3},
                        {"code": "SE953_P", "title": "قراءات فردية موجهة (موضوعات متقدمة)", "credits": 3},
                    ]
                }
            }
        }
    },
    # 6. Population Policies & Data Analysis
    {
        "name_en": "Population Policies & Data Analysis", "name_ar": "السياسات السكانية وتحليل بياناتها", "type": "Professional",
        "degrees": {
            "Diploma": {
                "desc_ar": "دبلوم في السياسات السكانية وتحليل بياناتها.",
                "courses": {
                    1: [
                        {"code": "PPDA101", "title": "السياسات والتوقعات السكانية", "credits": 3},
                        {"code": "PPDA102", "title": "مصادر البيانات السكانية وتقييمها", "credits": 3},
                        {"code": "PPDA103", "title": "السكان والتنمية (بشري - فقر - تمكين)", "credits": 3},
                        {"code": "PPDA104", "title": "استخدام SPSS لتحليل بيانات المسوح", "credits": 3},
                        {"code": "PPDA105", "title": "الإسقاطات السكانية باستخدام برنامج Spectrum", "credits": 3},
                    ],
                    2: [
                        {"code": "PPDA201", "title": "إسقاطات القوى العاملة ومؤشرات سوق العمل", "credits": 3},
                        {"code": "PPDA202", "title": "تحليل البيانات متعدد المستويات", "credits": 3},
                        {"code": "PPDA203", "title": "تحليل المسار والمعادلات البنائية باستخدام AMOS", "credits": 3},
                        {"code": "PPDA204", "title": "تطبيقات التحليل متعدد المتغيرات", "credits": 3},
                        {"code": "PPDA205", "title": "مشروع", "credits": 3},
                    ]
                }
            }
        }
    },
    # 7. Applied Statistics
    {
        "name_en": "Applied Statistics", "name_ar": "الإحصاءات التطبيقية", "type": "Academic",
        "degrees": {
            "Diploma": {
                "desc_ar": "دبلوم في الإحصاءات التطبيقية.",
                "courses": {
                    1: [
                        {"code": "AS101", "title": "مقدمة في الإحصاء التطبيقي", "credits": 3},
                        {"code": "AS102", "title": "مقدمة في المعاينة", "credits": 3},
                        {"code": "AS103", "title": "مقدمة في تحليل البيانات النوعية", "credits": 3},
                        {"code": "AS104", "title": "السلاسل الزمنية وتطبيقاتها", "credits": 3},
                        {"code": "AS105", "title": "تحليل البيانات باستخدام الحزم الإحصائية (1)", "credits": 3},
                    ],
                    2: [
                        {"code": "AS201", "title": "الأرقام القياسية", "credits": 3},
                        {"code": "AS202", "title": "تحليل الانحدار", "credits": 3},
                        {"code": "AS203", "title": "مقدمة في تحليل البيانات الكمية", "credits": 3},
                        {"code": "AS204", "title": "تحليل البيانات باستخدام الحزم الإحصائية (2)", "credits": 3},
                        {"code": "AS205", "title": "مشروع", "credits": 3},
                    ]
                }
            },
            "Master": {
                "desc_ar": "ماجستير في الإحصاءات التطبيقية.",
                "courses": {
                    1: [
                        {"code": "AS501", "title": "مبادئ ومنهجيات البحث العلمي", "credits": 3},
                        {"code": "AS502", "title": "تحليل البيانات النوعية", "credits": 3},
                        {"code": "AS503", "title": "تحليل البيانات الكمية", "credits": 3},
                    ],
                    2: [
                        {"code": "AS601", "title": "الاقتصاد القياسي", "credits": 3},
                        {"code": "AS602", "title": "مقدمة في التحليل متعدد المستويات", "credits": 3},
                        {"code": "AS603", "title": "التحليل متعدد المتغيرات", "credits": 3},
                        {"code": "AS604", "title": "مشروع", "credits": 6},
                    ]
                }
            },
            "PhD": {
                "desc_ar": "دكتوراه في الإحصاءات التطبيقية.",
                "courses": {
                    1: [
                        {"code": "AS901", "title": "تنقيب البيانات", "credits": 3},
                        {"code": "AS902", "title": "التحليل المتقدم متعدد المستويات", "credits": 3},
                        {"code": "AS903", "title": "مقدمة في البيانات الضخمة", "credits": 3},
                    ],
                    2: [
                        {"code": "AS951", "title": "أدوات تحليل البيانات الضخمة", "credits": 3},
                        {"code": "AS952", "title": "التحليل المتقدم متعدد المتغيرات", "credits": 3},
                        {"code": "AS953", "title": "قراءات فردية موجهة (موضوعات متقدمة)", "credits": 3},
                    ]
                }
            }
        }
    },
    # 8. Modern Management for Human Resources
    {
        "name_en": "Modern Management for Human Resources", "name_ar": "الإدارة الحديثة للموارد البشرية", "type": "Professional",
        "degrees": {
            "Diploma": {
                "desc_ar": "دبلوم في الإدارة الحديثة للموارد البشرية.",
                "courses": {
                    1: [
                        {"code": "HRM101", "title": "أساسيات ووظائف إدارة الموارد البشرية", "credits": 3},
                        {"code": "HRM102", "title": "نظام معلومات الموارد البشرية", "credits": 3},
                        {"code": "HRM103", "title": "تخطيط برامج التدريب", "credits": 3},
                        {"code": "HRM104", "title": "إدارة الإحلال الوظيفي", "credits": 3},
                        {"code": "HRM105", "title": "تنمية الموارد البشرية في إطار الجودة الشاملة", "credits": 3},
                    ],
                    2: [
                        {"code": "HRM201", "title": "قوانين العمل في مصر", "credits": 3},
                        {"code": "HRM202", "title": "تخطيط القوى العاملة", "credits": 3},
                        {"code": "HRM203", "title": "مقدمة في التحليل الإحصائي", "credits": 3},
                        {"code": "HRM204", "title": "الموارد البشرية والرضا الوظيفي", "credits": 3},
                        {"code": "HRM205", "title": "مشروع", "credits": 3},
                    ]
                }
            },
            "Master": {
                "desc_ar": "ماجستير في الإدارة الحديثة للموارد البشرية.",
                "courses": {
                    1: [
                        {"code": "HRM501", "title": "مبادئ ومنهجيات البحث العلمي", "credits": 3},
                        {"code": "HRM502", "title": "التخطيط الاستراتيجي للموارد البشرية", "credits": 3},
                        {"code": "HRM503", "title": "أخلاقيات العمل", "credits": 3},
                    ],
                    2: [
                        {"code": "HRM601", "title": "السلوك التنظيمي للموارد البشرية", "credits": 3},
                        {"code": "HRM602", "title": "تخطيط وإدارة المسار الوظيفي", "credits": 3},
                        {"code": "HRM603", "title": "قراءات فردية", "credits": 3},
                        {"code": "HRM604", "title": "مشروع", "credits": 6},
                    ]
                }
            },
            "PhD": {
                "desc_ar": "دكتوراه في الإدارة الحديثة للموارد البشرية.",
                "courses": {
                    1: [
                        {"code": "HRM901", "title": "التخطيط الاستراتيجي لإدارة الموارد البشرية", "credits": 3},
                        {"code": "HRM902", "title": "إدارة الموارد البشرية الدولية", "credits": 3},
                        {"code": "HRM903", "title": "الذكاء الاصطناعي والموارد البشرية", "credits": 3},
                    ],
                    2: [
                        {"code": "HRM951", "title": "الاستثمار البشري وإدارة رأس المال الفكري", "credits": 3},
                        {"code": "HRM952", "title": "الاتجاهات الحديثة في إدارة الموارد البشرية", "credits": 3},
                        {"code": "HRM953", "title": "قراءات فردية موجهة (موضوعات متقدمة)", "credits": 3},
                    ]
                }
            }
        }
    },
    # 9. Econometric Analysis of Time Series
    {
        "name_en": "Econometric Analysis of Time Series", "name_ar": "التحليل القياسي للسلاسل الزمنية", "type": "Academic",
        "degrees": {
            "Diploma": {
                "desc_ar": "دبلوم في التحليل القياسي للسلاسل الزمنية.",
                "courses": {
                    1: [
                        {"code": "EATS101", "title": "التحليل الإحصائي", "credits": 3},
                        {"code": "EATS102", "title": "السلاسل الزمنية ونماذج بوكس-جنكنز", "credits": 3},
                        {"code": "EATS103", "title": "طرق الاقتصاد القياسي", "credits": 3},
                        {"code": "EATS104", "title": "الطرق الرياضية للسلاسل الزمنية", "credits": 3},
                        {"code": "EATS105", "title": "حزم الحاسب الإحصائية والقياسية", "credits": 3},
                    ],
                    2: [
                        {"code": "EATS201", "title": "التنبؤ وجودة توافق النموذج", "credits": 3},
                        {"code": "EATS202", "title": "الاقتصاد القياسي المبني على السلاسل الزمنية", "credits": 3},
                        {"code": "EATS203", "title": "تطبيقات السلاسل الزمنية في مجالات مختلفة", "credits": 3},
                        {"code": "EATS204", "title": "تحليل بيانات البانل", "credits": 3},
                        {"code": "EATS205", "title": "مشروع", "credits": 3},
                    ]
                }
            },
            "Master": {
                "desc_ar": "ماجستير في التحليل القياسي للسلاسل الزمنية.",
                "courses": {
                    1: [
                        {"code": "EATS501", "title": "مبادئ ومنهجيات البحث العلمي", "credits": 3},
                        {"code": "EATS502", "title": "الطرق الرياضية المتقدمة للسلاسل الزمنية", "credits": 3},
                        {"code": "EATS503", "title": "الاحتمالات والإحصاء والعمليات العشوائية", "credits": 3},
                    ],
                    2: [
                        {"code": "EATS601", "title": "طرق الاقتصاد القياسي المتقدمة", "credits": 3},
                        {"code": "EATS602", "title": "السلاسل الزمنية أحادية المتغير", "credits": 3},
                        {"code": "EATS603", "title": "السلاسل الزمنية متعددة المتغيرات", "credits": 3},
                        {"code": "EATS604", "title": "مشروع", "credits": 6},
                    ]
                }
            }
        }
    },
    # 10. Statistical Computing
    {
        "name_en": "Statistical Computing", "name_ar": "الحسابات الإحصائية", "type": "Academic",
        "degrees": {
            "Diploma": {
                "desc_ar": "دبلوم في الحسابات الإحصائية.",
                "courses": {
                    1: [
                        {"code": "SCMP101", "title": "التحليل الإحصائي", "credits": 3},
                        {"code": "SCMP102", "title": "مقدمة في الإحصاء الرياضي", "credits": 3},
                        {"code": "SCMP103", "title": "الطرق الإحصائية والمحاكاة", "credits": 3},
                        {"code": "SCMP104", "title": "تكنولوجيا وبرمجيات الإنترنت", "credits": 3},
                        {"code": "SCMP105", "title": "الحزم الإحصائية", "credits": 3},
                    ],
                    2: [
                        {"code": "SCMP201", "title": "النماذج العشوائية وتطبيقاتها", "credits": 3},
                        {"code": "SCMP202", "title": "الحسابات التطورية والطبيعية", "credits": 3},
                        {"code": "SCMP203", "title": "السلاسل الزمنية والتنبؤ", "credits": 3},
                        {"code": "SCMP204", "title": "النمذجة الرياضية وتحليل القرار", "credits": 3},
                        {"code": "SCMP205", "title": "مشروع", "credits": 3},
                    ]
                }
            },
            "Master": {
                "desc_ar": "ماجستير في الحسابات الإحصائية.",
                "courses": {
                    1: [
                        {"code": "SCMP501", "title": "مبادئ ومنهجيات البحث العلمي", "credits": 3},
                        {"code": "SCMP502", "title": "التحليل العددي", "credits": 3},
                        {"code": "SCMP503", "title": "تحليل الانحدار", "credits": 3},
                    ],
                    2: [
                        {"code": "SCMP601", "title": "تقنيات المعاينة", "credits": 3},
                        {"code": "SCMP602", "title": "تحليل السلاسل الزمنية المتقدم", "credits": 3},
                        {"code": "SCMP603", "title": "حزم الحاسب في الإحصاء مع تطبيقات", "credits": 3},
                        {"code": "SCMP604", "title": "مشروع", "credits": 6},
                    ]
                }
            },
            "PhD": {
                "desc_ar": "دكتوراه في الحسابات الإحصائية.",
                "courses": {
                    1: [
                        {"code": "SCMP901", "title": "البرمجة الإحصائية باستخدام SAS", "credits": 3},
                        {"code": "SCMP902", "title": "التقنيات العددية المتقدمة", "credits": 3},
                        {"code": "SCMP903", "title": "الطرق غير البارامترية", "credits": 3},
                    ],
                    2: [
                        {"code": "SCMP951", "title": "البرمجة المتقدمة باستخدام Python و R", "credits": 3},
                        {"code": "SCMP952", "title": "الطرق الإحصائية في الموثوقية", "credits": 3},
                        {"code": "SCMP953", "title": "قراءات فردية موجهة (موضوعات متقدمة)", "credits": 3},
                    ]
                }
            }
        }
    },
    # 11. Statistical Quality Control & Quality Assurance
    {
        "name_en": "Statistical Quality Control & Quality Assurance", "name_ar": "الضبط الإحصائي وتوكيد الجودة", "type": "Professional",
        "degrees": {
            "Diploma": {
                "desc_ar": "دبلوم في الضبط الإحصائي وتوكيد الجودة.",
                "courses": {
                    1: [
                        {"code": "SQC101", "title": "أساسيات مراقبة الجودة", "credits": 3},
                        {"code": "SQC102", "title": "نظم المعلومات وإدارة المعرفة", "credits": 3},
                        {"code": "SQC103", "title": "خرائط المراقبة", "credits": 3},
                        {"code": "SQC104", "title": "تحليل البيانات", "credits": 3},
                        {"code": "SQC105", "title": "نظم الجودة", "credits": 3},
                    ],
                    2: [
                        {"code": "SQC201", "title": "إدارة المشروعات", "credits": 3},
                        {"code": "SQC202", "title": "معاينة القبول", "credits": 3},
                        {"code": "SQC203", "title": "الموثوقية والإحلال", "credits": 3},
                        {"code": "SQC204", "title": "التحسين المستمر", "credits": 3},
                        {"code": "SQC205", "title": "مشروع", "credits": 3},
                    ]
                }
            },
            "Master": {
                "desc_ar": "ماجستير في الضبط الإحصائي وتوكيد الجودة.",
                "courses": {
                    1: [
                        {"code": "SQC501", "title": "مبادئ ومنهجيات البحث العلمي", "credits": 3},
                        {"code": "SQC502", "title": "خرائط المراقبة المتقدمة", "credits": 3},
                        {"code": "SQC503", "title": "التنبؤ", "credits": 3},
                    ],
                    2: [
                        {"code": "SQC601", "title": "اتخاذ القرار", "credits": 3},
                        {"code": "SQC602", "title": "تصميم وتحليل التجارب", "credits": 3},
                        {"code": "SQC603", "title": "تحليل الكفاءة والإنتاجية", "credits": 3},
                        {"code": "SQC604", "title": "مشروع", "credits": 6},
                    ]
                }
            },
            "PhD": {
                "desc_ar": "دكتوراه في الضبط الإحصائي وتوكيد الجودة.",
                "courses": {
                    1: [
                        {"code": "SQC901", "title": "المحاكاة", "credits": 3},
                        {"code": "SQC902", "title": "المواصفات والتقييس", "credits": 3},
                        {"code": "SQC903", "title": "المراجعة الداخلية والخارجية", "credits": 3},
                    ],
                    2: [
                        {"code": "SQC951", "title": "إعادة الهندسة وإدارة التغيير", "credits": 3},
                        {"code": "SQC952", "title": "التحسين المستمر المتقدم", "credits": 3},
                        {"code": "SQC953", "title": "قراءات فردية موجهة (موضوعات متقدمة)", "credits": 3},
                    ]
                }
            }
        }
    },
    # 12. Risk and Crisis Management
    {
        "name_en": "Risk and Crisis Management", "name_ar": "إدارة المخاطر والأزمات", "type": "Professional",
        "degrees": {
            "Diploma": {
                "desc_ar": "دبلوم في إدارة المخاطر والأزمات.",
                "courses": {
                    1: [
                        {"code": "RCM101", "title": "إدارة الأزمات والمخاطر (1)", "credits": 3},
                        {"code": "RCM102", "title": "إدارة المخاطر المالية", "credits": 3},
                        {"code": "RCM103", "title": "تحليل البيانات الإحصائية وكتابة التقارير", "credits": 3},
                        {"code": "RCM104", "title": "دور القيادة في إدارة الأزمات", "credits": 3},
                        {"code": "RCM105", "title": "التخطيط الاستراتيجي لإدارة الأزمات", "credits": 3},
                    ],
                    2: [
                        {"code": "RCM201", "title": "دور الإعلام في إدارة الأزمات", "credits": 3},
                        {"code": "RCM202", "title": "بحوث العمليات", "credits": 3},
                        {"code": "RCM203", "title": "إدارة الأزمات والمخاطر (2)", "credits": 3},
                        {"code": "RCM204", "title": "التحليل العلمي للأزمات", "credits": 3},
                        {"code": "RCM205", "title": "مشروع", "credits": 3},
                    ]
                }
            },
            "Master": {
                "desc_ar": "ماجستير في إدارة المخاطر والأزمات.",
                "courses": {
                    1: [
                        {"code": "RCM501", "title": "مبادئ ومنهجيات البحث العلمي", "credits": 3},
                        {"code": "RCM502", "title": "التنبؤ الوقائي بالأزمات والمخاطر", "credits": 3},
                        {"code": "RCM503", "title": "التأمين في إدارة الأزمات والمخاطر", "credits": 3},
                    ],
                    2: [
                        {"code": "RCM601", "title": "التحليل الكمي للمخاطر", "credits": 3},
                        {"code": "RCM602", "title": "دور دعم القرار في إدارة الأزمات والمخاطر", "credits": 3},
                        {"code": "RCM603", "title": "قراءات فردية", "credits": 3},
                        {"code": "RCM604", "title": "مشروع", "credits": 6},
                    ]
                }
            },
            "PhD": {
                "desc_ar": "دكتوراه في إدارة المخاطر والأزمات.",
                "courses": {
                    1: [
                        {"code": "RCM901", "title": "التخطيط الاستراتيجي وسيناريوهات إدارة الأزمات", "credits": 3},
                        {"code": "RCM902", "title": "دور الحكومة في إدارة الأزمات والمخاطر", "credits": 3},
                        {"code": "RCM903", "title": "الذكاء الاصطناعي في إدارة الأزمات والمخاطر", "credits": 3},
                    ],
                    2: [
                        {"code": "RCM951", "title": "النظم المقارنة في إدارة الأزمات والمخاطر", "credits": 3},
                        {"code": "RCM952", "title": "المحاكاة", "credits": 3},
                        {"code": "RCM953", "title": "قراءات فردية موجهة (موضوعات متقدمة)", "credits": 3},
                    ]
                }
            }
        }
    },
    # 13. Surveys and Reporting
    {
        "name_en": "Surveys and Reporting", "name_ar": "المسوح وإعداد تقاريرها", "type": "Professional",
        "degrees": {
            "Diploma": {
                "desc_ar": "دبلوم في المسوح وإعداد تقاريرها.",
                "courses": {
                    1: [
                        {"code": "SR101", "title": "المسوح وأنواعها", "credits": 3},
                        {"code": "SR102", "title": "المعاينة", "credits": 3},
                        {"code": "SR103", "title": "إدخال البيانات باستخدام CSPro", "credits": 3},
                        {"code": "SR104", "title": "تحليل البيانات الوصفية (Metadata)", "credits": 3},
                        {"code": "SR105", "title": "تحليل بيانات الإنجاب", "credits": 3},
                    ],
                    2: [
                        {"code": "SR201", "title": "تنظيم الأسرة والحاجة غير الملباة (الصحة الإنجابية)", "credits": 3},
                        {"code": "SR202", "title": "الوفيات والمراضة", "credits": 3},
                        {"code": "SR203", "title": "تطبيقات البيانات متعددة المتغيرات", "credits": 3},
                        {"code": "SR204", "title": "إجراء تقارير المسوح ونشر نتائجها", "credits": 3},
                        {"code": "SR205", "title": "مشروع", "credits": 3},
                    ]
                }
            }
        }
    },
    # 14. Data Analysis
    {
        "name_en": "Data Analysis", "name_ar": "تحليل البيانات", "type": "Academic",
        "degrees": {
            "Diploma": {
                "desc_ar": "دبلوم في تحليل البيانات.",
                "courses": {
                    1: [
                        {"code": "DA101", "title": "مقدمة في الإحصاء", "credits": 3},
                        {"code": "DA102", "title": "مصادر البيانات وتقييمها", "credits": 3},
                        {"code": "DA103", "title": "مقدمة في تقنيات المعاينة", "credits": 3},
                        {"code": "DA104", "title": "تحليل الانحدار وتشخيصه", "credits": 3},
                        {"code": "DA105", "title": "تحليل البيانات باستخدام SPSS", "credits": 3},
                    ],
                    2: [
                        {"code": "DA201", "title": "مقدمة في تحليل البيانات النوعية", "credits": 3},
                        {"code": "DA202", "title": "مقدمة في تحليل البيانات الكمية", "credits": 3},
                        {"code": "DA203", "title": "مقدمة في تحليل البيانات متعدد المستويات", "credits": 3},
                        {"code": "DA204", "title": "مقدمة في التحليل متعدد المتغيرات", "credits": 3},
                        {"code": "DA205", "title": "مشروع", "credits": 3},
                    ]
                }
            },
            "Master": {
                "desc_ar": "ماجستير في تحليل البيانات.",
                "courses": {
                    1: [
                        {"code": "DA501", "title": "مبادئ ومنهجيات البحث العلمي", "credits": 3},
                        {"code": "DA502", "title": "تحليل البيانات النوعية", "credits": 3},
                        {"code": "DA503", "title": "تحليل البيانات الكمية", "credits": 3},
                    ],
                    2: [
                        {"code": "DA601", "title": "تنقيب البيانات مع تطبيقات", "credits": 3},
                        {"code": "DA602", "title": "موضوعات متقدمة في تحليل البيانات", "credits": 3},
                        {"code": "DA603", "title": "التحليل متعدد المتغيرات", "credits": 3},
                        {"code": "DA604", "title": "مشروع", "credits": 6},
                    ]
                }
            },
            "PhD": {
                "desc_ar": "دكتوراه في تحليل البيانات.",
                "courses": {
                    1: [
                        {"code": "DA901", "title": "التحليل النوعي المتقدم للبيانات", "credits": 3},
                        {"code": "DA902", "title": "التحليل الكمي المتقدم للبيانات", "credits": 3},
                        {"code": "DA903", "title": "التحليل المتقدم متعدد المتغيرات", "credits": 3},
                    ],
                    2: [
                        {"code": "DA951", "title": "التنقيب المتقدم في البيانات", "credits": 3},
                        {"code": "DA952", "title": "التحليل المتقدم متعدد المستويات", "credits": 3},
                        {"code": "DA953", "title": "قراءات فردية موجهة (موضوعات متقدمة)", "credits": 3},
                    ]
                }
            }
        }
    },
    # 15. Life Testing and Reliability Analysis
    {
        "name_en": "Life Testing and Reliability Analysis", "name_ar": "اختبارات الحياة وتحليل الصلاحية", "type": "Academic",
        "degrees": {
            "Diploma": {
                "desc_ar": "دبلوم في اختبارات الحياة وتحليل الصلاحية.",
                "courses": {
                    1: [
                        {"code": "LTRA101", "title": "الإحصاء والاحتمالات", "credits": 3},
                        {"code": "LTRA102", "title": "الإحصاء التطبيقي", "credits": 3},
                        {"code": "LTRA103", "title": "تحليل البقاء", "credits": 3},
                        {"code": "LTRA104", "title": "مقدمة في الموثوقية واختبارات الحياة", "credits": 3},
                        {"code": "LTRA105", "title": "الحزم الإحصائية", "credits": 3},
                    ],
                    2: [
                        {"code": "LTRA201", "title": "تحليل الموثوقية الإحصائي", "credits": 3},
                        {"code": "LTRA202", "title": "فترات التنبؤ والتسامح: القياس والموثوقية", "credits": 3},
                        {"code": "LTRA203", "title": "الطرق الإحصائية في الموثوقية", "credits": 3},
                        {"code": "LTRA204", "title": "تطبيقات الموثوقية واختبارات الحياة", "credits": 3},
                        {"code": "LTRA205", "title": "مشروع", "credits": 3},
                    ]
                }
            }
        }
    },
    # 16. Measuring Public Opinion Polls
    {
        "name_en": "Measuring Public Opinion Polls", "name_ar": "قياس استطلاعات الرأي العام", "type": "Professional",
        "degrees": {
            "Diploma": {
                "desc_ar": "دبلوم في قياس استطلاعات الرأي العام.",
                "courses": {
                    1: [
                        {"code": "MPOP101", "title": "دليل استطلاعات الرأي العام", "credits": 3},
                        {"code": "MPOP102", "title": "تصميم مسح الرأي العام", "credits": 3},
                        {"code": "MPOP103", "title": "وسائل المسح والقياس، فن المقابلات الشخصية، مدونة الأخلاقيات والممارسات المهنية", "credits": 3},
                        {"code": "MPOP104", "title": "تحليل بيانات المسح", "credits": 3},
                        {"code": "MPOP105", "title": "المجالات التي تغطيها استطلاعات الرأي العام", "credits": 3},
                    ],
                    2: [
                        {"code": "MPOP201", "title": "استخدام SPSS في تحليل بيانات المسح", "credits": 3},
                        {"code": "MPOP202", "title": "تحليل الاتجاه والمحتوى: تحليل متعمق", "credits": 3},
                        {"code": "MPOP203", "title": "إعداد تقارير المسح ونشر نتائجها", "credits": 3},
                        {"code": "MPOP204", "title": "أمثلة عملية لاستطلاعات الرأي العام، تقييم الأداء وضمان الجودة", "credits": 3},
                        {"code": "MPOP205", "title": "مشروع", "credits": 3},
                    ]
                }
            }
        }
    },
    # 17. Statistical Research and Development
    {
        "name_en": "Statistical Research and Development", "name_ar": "البحوث الإحصائية والتطوير", "type": "Professional",
        "degrees": {
            "Diploma": {
                "desc_ar": "دبلوم في البحوث الإحصائية والتطوير.",
                "courses": {
                    1: [
                        {"code": "SRD101", "title": "أساسيات البحث والتطوير (R & D)", "credits": 3},
                        {"code": "SRD102", "title": "تنقيب البيانات", "credits": 3},
                        {"code": "SRD103", "title": "التحسين المستمر", "credits": 3},
                        {"code": "SRD104", "title": "اتخاذ القرار", "credits": 3},
                        {"code": "SRD105", "title": "الإبداع والابتكار", "credits": 3},
                    ],
                    2: [
                        {"code": "SRD201", "title": "هندسة القيمة", "credits": 3},
                        {"code": "SRD202", "title": "إعادة الهندسة وإدارة التغيير", "credits": 3},
                        {"code": "SRD203", "title": "التنبؤ والإنذار المبكر", "credits": 3},
                        {"code": "SRD204", "title": "المحاكاة", "credits": 3},
                        {"code": "SRD205", "title": "مشروع", "credits": 3},
                    ]
                }
            },
            "Master": {
                "desc_ar": "ماجستير في البحوث الإحصائية والتطوير.",
                "courses": {
                    1: [
                        {"code": "SRD501", "title": "مبادئ ومنهجيات البحث العلمي", "credits": 3},
                        {"code": "SRD502", "title": "إدارة المشروعات", "credits": 3},
                        {"code": "SRD503", "title": "الذكاء الاصطناعي", "credits": 3},
                    ],
                    2: [
                        {"code": "SRD601", "title": "تحليل الأعمال", "credits": 3},
                        {"code": "SRD602", "title": "تحليل البيانات الذكي", "credits": 3},
                        {"code": "SRD603", "title": "تحليل المخاطر", "credits": 3},
                        {"code": "SRD604", "credits": 6, "title": "مشروع"},
                    ]
                }
            }
        }
    },
    # 18. Human Development & Resources
    {
        "name_en": "Human Development & Resources", "name_ar": "التنمية البشرية ومواردها", "type": "Professional",
        "degrees": {
            "Diploma": {
                "desc_ar": "دبلوم في التنمية البشرية ومواردها.",
                "courses": {
                    1: [
                        {"code": "HDR101", "title": "أساسيات التنمية البشرية", "credits": 3},
                        {"code": "HDR102", "title": "الصحة والتعليم والقوى العاملة والتنمية البشرية", "credits": 3},
                        {"code": "HDR103", "title": "تقدير التنمية البشرية", "credits": 3},
                        {"code": "HDR104", "title": "أساسيات السكان", "credits": 3},
                        {"code": "HDR105", "title": "الطرق الإحصائية", "credits": 3},
                    ],
                    2: [
                        {"code": "HDR201", "title": "مهارات الإدارة الأساسية", "credits": 3},
                        {"code": "HDR202", "title": "التنبؤ بالطلب على التنمية البشرية", "credits": 3},
                        {"code": "HDR203", "title": "اقتصاديات التنمية البشرية", "credits": 3},
                        {"code": "HDR204", "title": "الإسقاطات السكانية باستخدام حزم الحاسب", "credits": 3},
                        {"code": "HDR205", "title": "مشروع", "credits": 3},
                    ]
                }
            }
        }
    }
]

# Ensure all courses in all programs have a semester assigned
for prog in PROGRAM_DATA:
    for degree in prog.get('degrees', {}).values():
        for semester, courses in degree.get('courses', {}).items():
            for course in courses:
                if 'semester' not in course or course['semester'] is None:
                    course['semester'] = 1  # Default to semester 1, adjust as needed

def populate_database():
    """Populates the database with programs and courses in an idempotent way."""
    with app.app_context():
        # Create tables if they do not exist
        db.create_all()
        
        try:
            for program_data in PROGRAM_DATA:
                for degree_type, degree_info in program_data.get("degrees", {}).items():
                    program_name_en = program_data["name_en"]
                    program_name_ar = program_data["name_ar"]
                    program_type = program_data.get("type", "Professional")
                    desc_ar = degree_info.get("desc_ar", f"{degree_type} in {program_name_en}")

                    program = Program.query.filter_by(name=program_name_en, degree_type=degree_type).first()
                    
                    if not program:
                        program = Program(
                            name=program_name_en, degree_type=degree_type, description=desc_ar,
                            arabic_name=program_name_ar, arabic_description=desc_ar,
                            type=program_type, is_active=True
                        )
                        db.session.add(program)
                        db.session.flush()
                        logging.info(f"CREATED Program: {program.name} ({program.degree_type})")
                    else:
                        program.is_active = True
                        program.arabic_name = program_name_ar
                        program.type = program_type
                        program.description = desc_ar
                        program.arabic_description = desc_ar
                        logging.info(f"FOUND Program: {program.name} ({program.degree_type}). Ensuring it's up-to-date and active.")

                    for semester, courses_list in degree_info.get("courses", {}).items():
                        for course_info in courses_list:
                            course_code = course_info["code"]
                            course_title = course_info["title"]
                            course_credits = course_info["credits"]

                            course = Course.query.filter_by(code=course_code).first()
                            if not course:
                                # Corrected: The Course model does not take 'semester' as an argument.
                                course = Course(
                                    code=course_info["code"],
                                    title=course_info["title"],
                                    credits=course_info["credits"],
                                    description=course_info.get("description"),
                                    is_active=course_info.get("is_active", True)
                                )
                                db.session.add(course)
                                db.session.flush()
                                logging.info(f"  - CREATED Course: {course.code} - {course.title}")
                            else:
                                course.is_active = True
                                course.title = course_title
                                course.credits = course_credits
                                logging.info(f"  - FOUND Course: {course.code}. Ensuring it's up-to-date and active.")

                            association = ProgramCourse.query.filter_by(program_id=program.id, course_id=course.id).first()
                            if not association:
                                # The semester value comes from the loop variable here. This is correct.
                                new_association = ProgramCourse(
                                    program_id=program.id, course_id=course.id, semester=semester
                                )
                                db.session.add(new_association)
                                logging.info(f"    - ASSOCIATED Course {course.code} to Program {program.name} for Semester {semester}")
            
            db.session.commit()
            logging.info("--- Database population/update complete! ---")
        except Exception as e:
            logging.error(f"An error occurred: {e}", exc_info=True)
            db.session.rollback()

if __name__ == '__main__':
    logging.info("Starting database population script...")
    populate_database()
    logging.info("Script finished.")