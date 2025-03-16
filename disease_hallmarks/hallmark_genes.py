# 1. Genomic instability
genomic_instability_genes = [
    "BUBR1",  # BUB1B, mentioned in Otín - extends lifespan when overexpressed
    "SIRT6",  # Mentioned in Otín - improves double-strand break repair, reduces genomic instability, extends lifespan
    "LMNA",   # Mentioned in Otín - associated with progeria syndromes
    "BANF1",  # Mentioned in Otín - associated with progeria syndromes
    "ZMPSTE24",  # Mentioned in Otín - prelamin A processing
    "TP53",  # From Pun - tumor suppressor
    "ERCC1",  # From Pun - DNA repair
    "DNMT3",  # From Pun - linked to CHIP
    "TET2",  # Mentioned in Otín - linked to CHIP and inflammation
    "ABL1",  # From Pun
    "AKT1",  # From Pun
    "CASP1",  # From Pun
    "CASP3",  # From Pun
    "CASP8",  # From Pun
    "CAT",  # From Pun
    "CHUK",  # From Pun
    "CNOT6L",  # From Pun
    "CSNK1A1",  # From Pun
    "DNMT1",  # From Pun
    "DUSP3",  # From Pun
    "EGFR",  # From Pun
    "EP300",  # From Pun
    "ESR1",  # From Pun
    "HDAC1",  # From Pun
    "HGF",  # From Pun
    "IGF1",  # From Pun
    "IGF1R",  # From Pun
    "IKBKB",  # From Pun
    "IL1B",  # From Pun
    "JAK2",  # From Pun
    "KDR",  # From Pun
    "MAPK8",  # From Pun
    "MMP9",  # From Pun
    "MTOR",  # From Pun
    "PARP1",  # From Pun
    "PTEN",  # From Pun
    "PTK2",  # From Pun
    "RAB32",  # From Pun
    "RNF126",  # From Pun
    "ROCK1",  # From Pun
    "SIRT1",  # From Pun
]

# 2. Telomere attrition
telomere_attrition_genes = [
    "TERT",  # Mentioned in Otín - telomerase reverse transcriptase, extends lifespan when activated
    "TERC",  # Implied in Otín - telomerase RNA component
    "DDX21",  # From Pun
    "DNMT1",  # From Pun
    "IL1B",  # From Pun
    "MTOR",  # From Pun
    "PARP1",  # From Pun
    "POLA1",  # From Pun
    "SIRT1",  # From Pun
    "TGS1",  # From Pun
    "TNF",  # From Pun
]

# 3. Epigenetic alterations
epigenetic_alterations_genes = [
    "KAT7",  # Mentioned in Otín - inactivation extends lifespan
    "SIRT1",  # Mentioned in Otín - histone deacetylase
    "SIRT3",  # Mentioned in Otín - reverses regenerative capacity of HSC
    "SIRT6",  # Mentioned in Otín - extends lifespan
    "SIRT7",  # Mentioned in Otín - related to genomic stability
    "DNMT3",  # Mentioned in Otín
    "TET2",  # Mentioned in Otín
    "HP1a",  # Mentioned in Otín - heterochromatin protein
    "PIN1",  # Mentioned in Otín - preserves heterochromatin
    "miR-188-3p",  # Mentioned in Otín - targets skeletal endothelium
    "miR-455-3p",  # Mentioned in Otín - improves mitochondrial function
    "LINE1",  # Mentioned in Otín - retrotransposon reactivation in aging
    "AKT1",  # From Pun
    "DNMT1",  # From Pun
    "EP300",  # From Pun
    "EZH2",  # From Pun
    "HDAC1",  # From Pun
    "HDAC9",  # From Pun
    "IGF1",  # From Pun
    "KAT6A",  # From Pun
    "KAT8",  # From Pun
    "KDM7A",  # From Pun
    "MTOR",  # From Pun
    "MYO1C",  # From Pun
]

# 4. Loss of proteostasis
loss_of_proteostasis_genes = [
    "LAMP2A",  # Mentioned in Otín - lysosome-associated membrane protein 2A for CMA
    "HSP70",  # Mentioned in Otín - intranasal application extends lifespan
    "HSC70",  # Mentioned in Otín - for CMA
    "RPS23",  # Mentioned in Otín - improves translation accuracy, extends lifespan
    "RPS9",  # Mentioned in Otín - mutation causes premature aging
    "eIF2a",  # Mentioned in Otín - related to integrated stress response
    "UPR",  # Mentioned in Otín - unfolded protein response pathway
    "AKT1",  # From Pun
    "CDC34",  # From Pun
    "EGFR",  # From Pun
    "GAK",  # From Pun
    "HGF",  # From Pun
    "HSPA5",  # From Pun
    "IGF1",  # From Pun
    "IKBKB",  # From Pun
    "IL6",  # From Pun
    "MAPK1",  # From Pun
    "MAPK14",  # From Pun
    "MTOR",  # From Pun
    "PPARA",  # From Pun
    "PRKAG1",  # From Pun
    "PSMD14",  # From Pun
    "RAB13",  # From Pun
    "RAB31",  # From Pun
    "RAB33B",  # From Pun
    "RAB7A",  # From Pun
    "RAB7B",  # From Pun
    "RAB8B",  # From Pun
    "RNF5",  # From Pun
    "TLR2",  # From Pun
    "UCHL5",  # From Pun
    "UBE2E3",  # From Pun
    "UBE2M",  # From Pun
    "UBE2O",  # From Pun
    "UBE4A",  # From Pun
    "USP2",  # From Pun
    "VDR",  # From Pun
    "WWP1",  # From Pun
]

# 5. Disabled macroautophagy
disabled_macroautophagy_genes = [
    "ATG5",  # Mentioned in Otín - overexpression improves longevity
    "ATG7",  # Mentioned in Otín - expression declines with age
    "BECN1",  # Mentioned in Otín - mutation enhances autophagy, extends lifespan
    "TFEB",  # Mentioned in Otín - activated by spermidine
    "EP300",  # Mentioned in Otín - inhibited by spermidine to induce autophagy
    "eIF5A",  # Mentioned in Otín - hypusinated form essential for TFEB synthesis
    "mTORC1",  # Mentioned in Otín - inhibition induces autophagy
    "SIRT1",  # From Pun
    "GAK",  # From Pun
    "HSPA5",  # From Pun
    "PRKAG1",  # From Pun
    "PSMD14",  # From Pun
    "RAB13",  # From Pun
    "RAB31",  # From Pun
    "RAB33B",  # From Pun
    "RAB7A",  # From Pun
    "RAB7B",  # From Pun
    "RAB8B",  # From Pun
    "RNF5",  # From Pun
    "USP2",  # From Pun
]

# 6. Deregulated nutrient-sensing
deregulated_nutrient_sensing_genes = [
    "GH",  # Mentioned in Otín - growth hormone, receptor knockout extends lifespan
    "IGF1",  # Mentioned in Otín - insulin-like growth factor 1
    "IGF1R",  # Mentioned in Otín - inhibition extends lifespan
    "PI3K",  # Mentioned in Otín - dominant negative in heart extends lifespan
    "AKT",  # Mentioned in Otín - downstream of IGF1R
    "mTORC1",  # Mentioned in Otín - inhibition extends lifespan
    "AMPK",  # Mentioned in Otín - nutrient scarcity sensor
    "SIRT1",  # Mentioned in Otín - nutrient scarcity sensor
    "FOXO3",  # Mentioned in Otín - mentioned for human longevity
    "ALK",  # Mentioned in Otín - receptor responding to augmentor α and β
    "PLA2G7",  # Mentioned in Otín - platelet-activating factor acetylhydrolase
    "AKT1",  # From Pun
    "BLK",  # From Pun
    "CD36",  # From Pun
    "EGFR",  # From Pun
    "FGF2",  # From Pun
    "HGF",  # From Pun
    "IGF2",  # From Pun
    "IMPDH2",  # From Pun
    "INSR",  # From Pun
    "ITGAV",  # From Pun
    "KDR",  # From Pun
    "KIT",  # From Pun
    "MTOR",  # From Pun
    "NGF",  # From Pun
    "PIP5K1A",  # From Pun
    "PTEN",  # From Pun
    "RAB13",  # From Pun
    "RAB4B",  # From Pun
    "RRAGD",  # From Pun
    "VEGFA",  # From Pun
]

# 7. Mitochondrial dysfunction
mitochondrial_dysfunction_genes = [
    "mtDNA",  # Mentioned in Otín - mitochondrial DNA accumulates mutations with age
    "TFAM",  # Mentioned in Otín - T cell-specific defect accelerates aging
    "SIRT3",  # From Pun
    "POLG",  # Mentioned in Otín - DNA polymerase gamma deficiency accelerates aging
    "NAD+",  # Mentioned in Otín - precursors improve health
    "MOTS-c",  # Mentioned in Otín - mitochondrial-derived peptide
    "Humanin",  # Mentioned in Otín - mitochondrial-derived peptide, levels in centenarians
    "AKT1",  # From Pun
    "ARL2",  # From Pun
    "ATAD3B",  # From Pun
    "GAK",  # From Pun
    "HGF",  # From Pun
    "HSPA5",  # From Pun
    "IGF1",  # From Pun
    "IGF1R",  # From Pun
    "IL1B",  # From Pun
    "IL6",  # From Pun
    "ITGB2",  # From Pun
    "MTHFD2",  # From Pun
    "MTOR",  # From Pun
    "OLA1",  # From Pun
    "PRKAG1",  # From Pun
    "PSMD14",  # From Pun
    "RAB13",  # From Pun
    "RAB31",  # From Pun
    "RAB32",  # From Pun
    "RAB33B",  # From Pun
    "RAB7A",  # From Pun
    "RAB7B",  # From Pun
    "RAB8B",  # From Pun
    "RHOT1",  # From Pun
    "RHOT2",  # From Pun
    "RNF14",  # From Pun
    "RNF5",  # From Pun
    "SOD2",  # From Pun
    "SRC",  # From Pun
    "TLR4",  # From Pun
    "USP2",  # From Pun
]

# 8. Cellular senescence
cellular_senescence_genes = [
    "CDKN2A",  # Mentioned in Otín - p16INK4a, genetic ablation increases lifespan
    "TP53",  # Mentioned in Otín
    "CDKN1A",  # Mentioned in Otín - p21
    "RB1",  # Mentioned in Otín - retinoblastoma protein
    "LMNB1",  # Mentioned in Otín - lamin B1, declines during senescence
    "HMGB1",  # From Pun
    "GPNMB",  # Mentioned in Otín - antibodies against it attenuate senescence
    "uPAR",  # Mentioned in Otín - CAR T cells against it attenuate senescence
    "SASP",  # Mentioned in Otín - senescence-associated secretory phenotype
    "FOXM1",  # Mentioned in Otín - cyclic induction extends lifespan
    "AKT1",  # From Pun
    "AR",  # From Pun
    "CHUK",  # From Pun
    "CNOT6L",  # From Pun
    "DUSP3",  # From Pun
    "EGFR",  # From Pun
    "EGLN1",  # From Pun
    "EP300",  # From Pun
    "EZH2",  # From Pun
    "HDAC6",  # From Pun
    "HGF",  # From Pun
    "IGF1",  # From Pun
    "IKBKB",  # From Pun
    "IL6",  # From Pun
    "JAK2",  # From Pun
    "KAT6A",  # From Pun
    "MMP1",  # From Pun
    "MTOR",  # From Pun
    "MYSM1",  # From Pun
    "PARP1",  # From Pun
    "PTEN",  # From Pun
    "PTK2",  # From Pun
    "ROCK1",  # From Pun
    "SRC",  # From Pun
    "TGFB1",  # From Pun
    "TGFBR2",  # From Pun
    "TNIK",  # From Pun
    "UBE2E3",  # From Pun
]

# 9. Stem cell exhaustion
stem_cell_exhaustion_genes = [
    "OCT4",  # Mentioned in Otín - part of OSKM reprogramming factors
    "SOX2",  # Mentioned in Otín - part of OSKM reprogramming factors
    "KLF4",  # Mentioned in Otín - part of OSKM reprogramming factors
    "MYC",  # Mentioned in Otín - part of OSKM reprogramming factors
    "OSKM",  # Mentioned in Otín - collective name for reprogramming factors
    "OSK",  # Mentioned in Otín - subset used for eye restoration
    "AKT1",  # From Pun
    "BMP2",  # From Pun
    "CXCL12",  # From Pun
    "CXCR4",  # From Pun
    "DNMT1",  # From Pun
    "EGLN1",  # From Pun
    "EP300",  # From Pun
    "FGF2",  # From Pun
    "GSK3B",  # From Pun
    "HGF",  # From Pun
    "IGF1",  # From Pun
    "IGF1R",  # From Pun
    "IGF2",  # From Pun
    "IKBKB",  # From Pun
    "IL1B",  # From Pun
    "IL6",  # From Pun
    "KAT6A",  # From Pun
    "MAPK14",  # From Pun
    "MTOR",  # From Pun
    "MYSM1",  # From Pun
    "NME7",  # From Pun
    "PPARA",  # From Pun
    "RAB5C",  # From Pun
    "ROCK1",  # From Pun
    "SETD1B",  # From Pun
    "SIRT1",  # From Pun
    "SPP1",  # From Pun
    "TGFB1",  # From Pun
    "TNIK",  # From Pun
    "UBE2E3",  # From Pun
]

# 10. Altered intercellular communication
altered_intercellular_communication_genes = [
    "CCL11",  # Mentioned in Otín - eotaxin, pro-aging blood factor
    "B2M",  # Mentioned in Otín - beta-2-microglobulin, pro-aging factor
    "IL6",  # Mentioned in Otín - pro-inflammatory cytokine
    "TGFB",  # Mentioned in Otín - transforming growth factor beta
    "CCL3",  # Mentioned in Otín - MIP-1 alpha, rejuvenating factor
    "TIMP2",  # Mentioned in Otín - rejuvenates hippocampus
    "IL37",  # Mentioned in Otín - improves metabolism and exercise
    "GDF11",  # Mentioned in Otín - rejuvenates tissues but has pro-fibrotic effects
    "VEGF",  # Mentioned in Otín - transgenic overexpression improves health
    "YAP",  # Mentioned in Otín - rejuvenates old cells
    "TAZ",  # Mentioned in Otín - works with YAP
    "AAK1",  # From Pun
    "ADAM17",  # From Pun
    "AKT1",  # From Pun
    "CHD9",  # From Pun
    "CXCL12",  # From Pun
    "EGLN1",  # From Pun
    "FZD8",  # From Pun
    "GSK3B",  # From Pun
    "HGF",  # From Pun
    "IGF1",  # From Pun
    "IMPDH2",  # From Pun
    "ITGAV",  # From Pun
    "ITGB5",  # From Pun
    "JAK2",  # From Pun
    "KDM7A",  # From Pun
    "MIB2",  # From Pun
    "MMP1",  # From Pun
    "MTMR4",  # From Pun
    "MTOR",  # From Pun
    "NOTCH1",  # From Pun
    "PJA2",  # From Pun
    "PPIL4",  # From Pun
    "PPM1A",  # From Pun
    "RAB5C",  # From Pun
    "RAB8B",  # From Pun
    "RHOA",  # From Pun
    "RHOU",  # From Pun
    "SIRT1",  # From Pun
    "TGFB1",  # From Pun
    "TNIK",  # From Pun
    "TNF",  # From Pun
    "UBE2M",  # From Pun
    "USP2",  # From Pun
]

# 11. Chronic inflammation
chronic_inflammation_genes = [
    "TNFA",  # Mentioned in Otín - TNF-alpha blockade prevents sarcopenia
    "IFNAR1",  # Mentioned in Otín - blockade reverses monocyte accumulation
    "EP2",  # Mentioned in Otín - prostaglandin E2 receptor, knockout improves cognition
    "NLRP3",  # Mentioned in Otín - knockout improves metabolism and extends lifespan
    "IL1B",  # Mentioned in Otín - canakinumab (anti-IL1B) reduces disease incidence
    "IL6",  # Mentioned in Otín - inflammatory marker predicting mortality
    "CRP",  # Mentioned in Otín - inflammatory biomarker
    "CHIP",  # Mentioned in Otín - clonal hematopoiesis of indeterminate potential
    "AKT1",  # From Pun
    "AR",  # From Pun
    "BRCC3",  # From Pun
    "CASP1",  # From Pun
    "CASP3",  # From Pun
    "CASP8",  # From Pun
    "CD36",  # From Pun
    "CLEC5A",  # From Pun
    "CSNK1A1",  # From Pun
    "CXCL12",  # From Pun
    "CXCR4",  # From Pun
    "DDX17",  # From Pun
    "DNMT1",  # From Pun
    "EGFR",  # From Pun
    "EGLN1",  # From Pun
    "EZH2",  # From Pun
    "HCK",  # From Pun
    "HGF",  # From Pun
    "IKBKB",  # From Pun
    "IGF1",  # From Pun
    "IGF1R",  # From Pun
    "ITGAM",  # From Pun
    "ITK",  # From Pun
    "JAK1",  # From Pun
    "JAK2",  # From Pun
    "KDR",  # From Pun
    "LOX",  # From Pun
    "LPIN2",  # From Pun
    "LYN",  # From Pun
    "MAPK1",  # From Pun
    "MMP2",  # From Pun
    "MTOR",  # From Pun
    "MYSM1",  # From Pun
    "NEK7",  # From Pun
    "PELI1",  # From Pun
    "PPM1A",  # From Pun
    "RAB7B",  # From Pun
    "RNF125",  # From Pun
    "SIRT1",  # From Pun
    "SPP1",  # From Pun
    "TLR2",  # From Pun
    "TLR4",  # From Pun
    "TNF",  # From Pun
    "UCHL5",  # From Pun
    "VDR",  # From Pun
    "VEGFA",  # From Pun
]

# 12. Dysbiosis
# dysbiosis_genes = [
    # The Otín paper primarily discusses microbiome composition rather than specific 
    # human genes for dysbiosis, focusing on interventions like fecal microbiota 
    # transplantation, probiotics, and microbiome-derived metabolites like SCFAs
    # and indoles, without clearly identifying specific human genes
# ]