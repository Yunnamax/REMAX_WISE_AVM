# Portuguese Real Estate Data Pipeline

**Automated ETL system for aggregating and analyzing property data from multiple Portuguese portals.**

![Python 3.10](https://img.shields.io/badge/python-3.10-blue)
![Status: Active Development](https://img.shields.io/badge/status-active_development-yellow)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

## Overview

This project automates the collection, cleaning, and standardization of real estate data from various Portuguese property portals. The system transforms raw listing data from sources like Idealista and Imovirtual into structured, analysis-ready datasets suitable for market research, price forecasting, and investment analysis.

The pipeline follows modern data engineering practices with a focus on configurability, maintainability, and scalability. It implements a multi-layer architecture that separates raw data storage from processed analytics-ready data.

## Architecture

The system implements a three-layer data architecture commonly used in modern data platforms:

**Data Flow**: Source APIs → Bronze (raw) → Silver (cleaned) → Gold (analytics, in development)

### Data Layers

1. **Bronze Layer**: Stores raw JSON data as received from data sources with minimal transformation
2. **Silver Layer**: Contains cleaned, validated, and standardized data ready for analysis
3. **Gold Layer**: Aggregated analytics and business intelligence data (planned)

### System Components

- **Configuration-Driven Orchestrator**: Routes and processes data based on YAML configurations
- **Modular Processors**: Source-specific data transformers that follow a common interface
- **Schema Registry**: Manages data schemas for validation and consistency
- **Idempotency Tracker**: Ensures safe reprocessing without data duplication
- **Metrics Collector**: Tracks processing statistics and pipeline performance

## Features

### Currently Implemented

- **Multi-source Ingestion**: Support for multiple Portuguese real estate portals
- **Configuration-Driven Processing**: Dynamic routing and transformation rules via YAML files
- **Data Validation**: Schema-based validation against predefined data contracts
- **Idempotent Operations**: Safe reprocessing with file-level tracking
- **Batch Processing**: Efficient group-based processing of related files
- **Comprehensive Logging**: Detailed processing logs for debugging and monitoring
- **Error Handling**: Graceful error recovery and detailed error reporting

### In Development

- Additional data source integrations
- Advanced data quality checks
- Performance optimizations for large datasets
- Enhanced monitoring and alerting

## Installation and Usage

### Prerequisites

- Python 3.10 or higher
- Git LFS (for handling large configuration files)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/Yunnamax/REMAX_WISE_AVM.git
cd REMAX_WISE_AVM

# Create and activate virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the Bronze to Silver pipeline
python -m src.data_pipeline.bronze_to_silver_coordinator
Project Structure
text
remax_wise_avm/
├── config/
│   ├── geospatial/
│   │   ├── district_boundaries/
│   │   └── location_names/
│   ├── path_patterns/
│   │   ├── bronze/
│   │   └── silver/
│   ├── processors_mapping/
│   │   ├── bronze_silver/
│   │   └── silver_gold/
│   ├── schemas/
│   │   ├── bronze/
│   │   ├── silver/
│   │   └── gold/
│   └── selectors/
│       └── idealista/
├── data/
│   └── bronze/
│       ├── archello/
│       ├── architizer/
│       ├── empresite/
│       ├── google_maps/
│       └── idealista/
├── logs/
│   ├── errors/
│   ├── research/
│   └── scraping/
├── metadata/
├── notebooks/
│   ├── data_exploration/
│   ├── modeling/
│   └── research/
├── src/
│   ├── data_pipeline/
│   │   └── processors/
│   ├── gold/
│   ├── research/
│   │   └── idealista/
│   └── scrapers/
│       ├── architecture/
│       ├── idealista/
│       └── municipalities/
└── tests/
    ├── data_pipeline/
    ├── research/
    └── scrapers/
Key Directories Explained
config/: Contains all configuration files separated by functionality

data/bronze/: Stores raw data collected from various sources (excluded from git)

src/data_pipeline/: Core ETL implementation with modular processors

src/scrapers/: Web scraping modules organized by data source

notebooks/: Jupyter notebooks for data exploration and research

tests/: Comprehensive test suites

Configuration
The system uses YAML configuration files to define processing rules, making it highly adaptable to new data sources and requirements.

Source Configuration
Each data source type has its own configuration file defining:

Grouping keys: How to combine related files for processing

Processor keys: How to select the appropriate processor for each file

Field mappings: How source-specific fields map to standardized schemas

Example configuration (config/path_patterns/bronze/real_estate_portal.yaml):

yaml
grouping_keys: [property_type, date]
processor_keys: [source, property_type]
components:
  - name: property_type
    position: 1
    prefix: "type="
  - name: date
    position: 2
    prefix: "date="
Processor Mapping
Processors are dynamically loaded based on configuration, allowing for easy extension:

yaml
processors:
  idealista.apartment_rent:
    module: "src.data_pipeline.processors.bronze_to_silver.idealista.apartments_rent_processor"
    class: "IdealistaApartmentRentProcessor"
Roadmap
Q2 2024
Add support for additional Portuguese real estate portals (Fotocasa, OLX Portugal)

Implement Gold layer for aggregated analytics and business intelligence

Develop data quality monitoring and alerting system

Q3 2024
Create data visualization dashboards for market trends

Implement predictive pricing models

Add geographic data integration (districts, transportation, amenities)

Q4 2024
Develop REST API for data access

Implement automated reporting system

Add support for commercial property types

Contributing
This project is under active development. Contributions are welcome in the following areas:

New Data Sources: Adding processors for additional Portuguese real estate portals

Data Quality: Enhancing validation rules and quality checks

Documentation: Improving documentation and code comments

Testing: Adding unit and integration tests

Please follow these steps to contribute:

Fork the repository

Create a feature branch (git checkout -b feature/amazing-feature)

Commit your changes (git commit -m 'Add some amazing feature')

Push to the branch (git push origin feature/amazing-feature)

Open a Pull Request

Before starting work on a major feature, please open an issue to discuss the proposed changes.

Tech Stack
Python 3.10: Primary programming language

Pandas: Data manipulation and transformation

PyYAML: Configuration file parsing

Apache Parquet: Efficient columnar data storage

Git LFS: Large file storage for geospatial data

Pathlib: Modern file path handling

Data Privacy and Compliance
This project is designed for educational and analytical purposes. Users are responsible for:

Complying with the terms of service of data sources

Respecting data privacy regulations (GDPR, LGPD)

Using data ethically and responsibly

The project does not include proprietary data or violate any platform terms of service.

License
This project is licensed under the MIT License - see the LICENSE file for details.

Acknowledgments
Data provided by Portuguese real estate portals for educational purposes

Inspired by modern data engineering practices and multi-layer data architectures

Built with support from the open-source community

Note: This project is under active development. Architecture and features may change as the project evolves.
