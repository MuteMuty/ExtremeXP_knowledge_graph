# ExtremeXP Use Cases: Domain Preparation & Entity Definitions

## 1. ADS (Situational Intelligence for PPDR)

### Domain Preparation
Focuses on enabling PPDR personnel to regenerate experiments, compare results, and make data-driven decisions using workflows and access control policies.

### Entities

| Entity                | Definition                                                                 | Key Attributes                                  | Relationships                              |
|-----------------------|---------------------------------------------------------------------------|-----------------------------------------------|-------------------------------------------|
| User                  | Researchers or PPDR officers interacting with the platform                | User ID, Role, Permissions                    | Uploads datasets, Creates experiments     |
| Dataset               | Structured/unstructured data files (e.g., sensor logs)                    | Dataset ID, Timestamp, Source, Schema         | Tagged with metadata, Used in experiments |
| Experiment            | Series of steps to achieve a specific intent                              | Experiment ID, Intent, Variability space      | Cloned from past experiments              |
| Workflow              | Sequence of tasks designed via graphical editors                          | Workflow ID, Variability points               | Includes reusable tasks                   |
| AccessControlPolicy   | Rules defining dataset/experiment accessibility                           | Policy ID, Scope, Constraints                 | Enforced during execution                 |
| Intent                | High-level objective of an experiment                                     | Intent ID, Description, Constraints           | Guides workflow generation                |
| VisualizationModule   | Interface for monitoring/comparing results                                | Module ID, Supported metrics                  | Displays experiment progress              |

---

## 2. i2CAT (Cyber Threat Classification)

### Domain Preparation
Focuses on balancing threat class distributions and improving classification accuracy via data augmentation.

### Entities

| Entity                | Definition                                                                 | Key Attributes                                  | Relationships                              |
|-----------------------|---------------------------------------------------------------------------|-----------------------------------------------|-------------------------------------------|
| ThreatDataset         | Labeled datasets containing cyber threats                                 | Dataset ID, Threat types, Class distribution  | Augmented by synthetic data               |
| SyntheticData         | Artificially generated samples                                            | Generation method, Target class               | Balances ThreatDataset                    |
| DataAugmentationTool  | Module for generating synthetic data                                      | Tool ID, Techniques                           | Integrated into workflows                 |
| ClassificationWorkflow| Pipeline for training threat classifiers                                  | Workflow ID, Algorithms, Metrics              | Uses ThreatDataset                        |

---

## 3. MobyX (AutoML for Activity Prediction)

### Domain Preparation
Combines AutoML workflows with human-in-the-loop validation for activity prediction.

### Entities

| Entity                | Definition                                                                 | Key Attributes                                  | Relationships                              |
|-----------------------|---------------------------------------------------------------------------|-----------------------------------------------|-------------------------------------------|
| GeolocationData       | GPS traces from travelers                                                 | Traveler ID, Timestamp, Coordinates           | Segmented into activities                 |
| Segmentation          | Algorithmic division of activities                                        | Segment ID, Predicted activity                | Adjusted by user                          |
| AutoMLModel           | ML model for activity prediction                                          | Model ID, Algorithm                           | Trained on GeolocationData                |
| GroundTruth           | Human-validated activity labels                                           | Validator ID, Confidence score                | Corrects Segmentation                     |

---

## 4. IDEKO (Anomaly Detection in Machinery)

### Domain Preparation
Detects industrial machinery anomalies using reusable tasks and dynamic experimentation.

### Entities

| Entity                | Definition                                                                 | Key Attributes                                  | Relationships                              |
|-----------------------|---------------------------------------------------------------------------|-----------------------------------------------|-------------------------------------------|
| SensorData            | Time-series data from machinery                                           | Sensor ID, Timestamp, Value                   | Preprocessed by reusable tasks            |
| AnomalyLabel          | Tags indicating normal/anomalous states                                   | Label ID, Severity, Type                      | Assigned to SensorData                    |
| ReusableTask          | Predefined workflow components                                            | Task ID, Code, Runtime environment            | Shared across experiments                 |
| BinaryClassifier      | Model for normal vs. anomalous states                                    | Model ID, Threshold                           | Switched from multi-class classifiers     |

---

## 5. CS (Flood Prediction)

### Domain Preparation
Generates spatial flood risk maps and integrates new datasets for disaster response.

### Entities

| Entity                | Definition                                                                 | Key Attributes                                  | Relationships                              |
|-----------------------|---------------------------------------------------------------------------|-----------------------------------------------|-------------------------------------------|
| FloodSensorData       | Environmental data from IoT sensors                                       | Sensor ID, Location, Value                    | Aggregated into spatial maps              |
| SpatialMap            | Geographic visualization of flood risks                                   | Map ID, Resolution, Risk thresholds           | Guides intervention plans                 |
| InterventionPlan      | Strategies for mitigating flood impact                                    | Plan ID, Priority zones                       | Triggered by SpatialMap                   |
| CityModel             | Custom predictive model for city-specific floods                         | Model ID, City name                           | Trained on FloodSensorData                |
