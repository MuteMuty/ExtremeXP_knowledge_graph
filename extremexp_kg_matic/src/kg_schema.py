from rdflib import Namespace, RDF, RDFS, OWL, XSD

# Define your base namespace
EX = Namespace("http://extremexp.eu/ontology/matic_papers/")

# Classes
Paper = EX.Paper
Task = EX.Task
Dataset = EX.Dataset
Method = EX.Method
ModelConfiguration = EX.ModelConfiguration
ReportedResult = EX.ReportedResult

# Datatype Properties for Paper
paper_title = EX.paperTitle # string
paper_pdfUrl = EX.pdfUrl # string (xsd:anyURI)
paper_papersWithCodeUrl = EX.papersWithCodeUrl # string (xsd:anyURI)
paper_year = EX.year # integer (xsd:gYear or xsd:integer)

# Datatype Properties for Task
task_name = EX.taskName # string

# Datatype Properties for Dataset
dataset_name = EX.datasetName # string

# Datatype Properties for Method
method_name = EX.methodName # string

# Datatype Properties for ModelConfiguration
mc_configurationString = EX.configurationString # string

# Datatype Properties for ReportedResult
rr_metricName = EX.metricName # string
rr_metricValue = EX.metricValue # string (or xsd:float, xsd:decimal)
rr_rank = EX.rank # integer (xsd:integer)

# Object Properties (Relationships)
# For Paper
paper_mentionsTask = EX.mentionsTask       # Paper -> Task
paper_mentionsDataset = EX.mentionsDataset # Paper -> Dataset
paper_reportsResult = EX.reportsResult     # Paper -> ReportedResult
paper_employsMethod = EX.employsMethod     # Paper -> Method

# For ReportedResult
rr_evaluatesTask = EX.evaluatesTask             # ReportedResult -> Task
rr_onDataset = EX.onDataset                   # ReportedResult -> Dataset
rr_achievedByModel = EX.achievedByModel       # ReportedResult -> ModelConfiguration
rr_reportedInPaper = EX.reportedInPaper         # ReportedResult -> Paper (Inverse of paper_reportsResult)


# You can also define rdfs:label or rdfs:comment for your terms here if you build a full ontology
# e.g.,
# G.add((Paper, RDFS.label, Literal("Scientific Paper")))
# G.add((paper_title, RDFS.domain, Paper))
# G.add((paper_title, RDFS.range, XSD.string))
