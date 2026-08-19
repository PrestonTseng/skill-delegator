# railML 3.3 vs EULYNX Data Preparation 1.2

Condensed primary-source notes for evaluating railway infrastructure exchange formats and site-level SSOTs.

## railML 3.3

- **Role:** XML/XSD exchange interface across railway applications, with Infrastructure and Interlocking subschemas among its main areas.
- **Topology and track:** Infrastructure uses a graph-based topology concept derived from RailTopoModel; railML 3.3 is based on RailTopoModel 1.5 and supports multiple aggregation levels.
- **Location and geometry:** Supports geographic coordinates such as WGS84/GML, linear positioning/mileage, screen coordinates, track radius, and gradient.
- **Assets:** Infrastructure includes signals, track circuits, balises, platforms, level crossings, and other located elements. Interlocking explicitly covers signals, switches, TVP sections, signal boxes, and RBC relationships.
- **Routes/interlocking:** The Interlocking subschema targets route safety and conflicting-movement prevention; official use cases include Interlocking Engineering, ETCS track net, and simulation. Do not infer complete locking semantics without checking the chosen use-case profile and XSD fields.
- **Serialization:** XML described by XSD; official XSD outranks HTML documentation and wiki text when contradictory.
- **Maturity:** Version 3.3 released 2024-11-05 for productive use; SR1 documentation is published; end of support not yet announced.
- **Licensing:** The official site calls railML open source/open data, but 3.x schemas use restricted CC BY-NC-ND 4.0 terms. Registration is required before interface implementation; certification is mandatory before productive/commercial interface use; schema redistribution is restricted to railML.org. After certification, the interface may receive CC BY-ND terms allowing commercial use. Report these legal constraints rather than treating “open” as equivalent to a permissive or OSI-style license.
- **SSOT assessment:** Strong candidate for a canonical **exchange** model if a project freezes a version/use-case profile and defines ID, mandatory-field, extension, validation, and migration policies. It is not itself an authoring database or transaction model; an internal domain store with railML import/export may be preferable.

Official URLs:

- https://www.railml.org/en/about-railml
- https://www.railml.org/en/subschemas
- https://www.railml.org/en/subschemas/infrastructure
- https://www.railml.org/en/subschemas/interlocking
- https://www.railml.org/en/news/railml-3-3-overview-of-key-developments
- https://www.railml.org/en/documentation-railml3
- https://www.railml.org/en/schemas
- https://www.railml.org/en/licence
- https://www.railml.org/en/version-timeline

## EULYNX Data Preparation 1.2

- **Role:** Information model for exchange of signalling-engineering and configuration data between infrastructure managers and suppliers/engineering companies.
- **Model breadth:** Generic domain includes data container, GEO information, project management, and common classes. Signalling domain includes Track, Signal, Point/Crossing/Derailer, Train Detection, Route, Automatic Route Setting, Flank Protection, ETCS, level crossings, speed profiles, and further signalling assets. National domains exist for multiple infrastructure managers.
- **Topology and geometry:** The published model includes RSM topology/network-topology and RSM geometry packages, including horizontal/vertical alignment and related location concepts.
- **Routes/interlocking:** The HTML model explicitly contains route overview/body, conflicting routes, route conditions, flank protection, and point/crossing topology. This is deeper signalling-engineering application data than a generic geographic route.
- **Serialization:** UML information model published as XMI; official XML schemata are provided as zipped XSD. Domains map to XSD namespaces.
- **Licensing:** Released under EUPL 1.2; XSD, XMI, and HTML model are publicly available.
- **Maturity warning:** The official archive states that development has stopped and the model is currently not maintained. Treat it as frozen/legacy despite broad semantic coverage.
- **SSOT assessment:** Useful as a legacy exchange contract or semantic reference. Do not recommend it as the sole long-term SSOT for a new system unless the adopter deliberately freezes v1.2 and accepts responsibility for schema governance, defect correction, national extensions, and migrations.

Official URLs:

- https://eulynx.eu/2023/12/15/eulynx-dataprep-the-information-model-for-signalling-engineering/
- https://eulynx.eu/resource-hub-dataprep-model/
- https://eulynx.eu/dataprep-2023-03/
- https://eulynx.eu/dataprep-2023-03/EARoot/EA3/EA2/EA2/EA11583.htm
- https://eulynx.eu/dataprep-2023-03/EARoot/EA3/EA2/EA6/EA11883.htm
- https://eulynx.eu/dataprep-2023-03/EARoot/EA2/EA4/EA7/EA8793.htm
- https://eulynx.eu/dataprep-2023-03/EARoot/EA2/EA4/EA7/EA8803.htm
- https://eulynx.eu/dataprep-2023-03/EARoot/EA2/EA4/EA1/EA10/EA6790.htm
- https://eulynx.eu/dataprep-2023-03/EARoot/EA2/EA4/EA4/EA8080.htm

## Reusable decision rule

Separate three questions:

1. Does the model carry the required semantics?
2. Is it a maintained interchange standard with workable legal terms?
3. Is it suitable as the mutable authoring SSOT, or only as a canonical exchange representation?

Semantic richness alone does not make an archived model a sustainable SSOT, and calling a format “open” does not answer registration, certification, redistribution, or derivative-work restrictions.