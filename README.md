---

# AWS Resource Tagging Script 

This script interacts with AWS services and a PostgreSQL database to fetch resource tags, process them, and store the relevant data in a PostgreSQL database.

## Features

- **Fetch Resource Tags**: Retrieves tags for various AWS resources, including Load Balancers (ELB), ElastiCache clusters, RDS instances, SQS queues, and EC2 instances.
- **Store Data in PostgreSQL**: Inserts or updates resource information into a PostgreSQL database table.
- **Customizable**: Allows user input for AWS tag key, AWS regions, database connection details, and table names.

## Prerequisites

- **Python 3.9**
- **AWS Credentials**: Ensure that your AWS credentials are configured (e.g., via AWS CLI - *aws configure* or environment variables).
- **Python Packages**:
  - `boto3`: AWS SDK for Python.
  - `sqlalchemy`: SQL toolkit and Object-Relational Mapping (ORM) library.
  - `psycopg2`: PostgreSQL adapter for Python.

Install the required packages using pip:

```bash
pip install boto3 sqlalchemy psycopg2
```
or
```bash
pip3  install -r requirements.txt
```


## Usage

1. **Prepare Your Environment**: Ensure you have valid AWS credentials and a PostgreSQL database setup.

2. **Run the Script**: Execute the script using Python.

```bash
python resimport.py
```

3. **Provide Inputs**: When prompted, provide the following inputs:
   - **AWS Tag Key**: The key used for tagging AWS resources (e.g., `customer`).
   - **AWS Regions**: Comma-separated list of AWS regions to process (e.g., `us-west-2,eu-central-1`).
   - **Database URL**: The connection URL for your PostgreSQL database in the format `postgresql+psycopg2://username:password@host:port/database_name`.
   - **Table Name**: The name of the table where data will be stored (e.g., `aws_resources`).

## How It Works

- **Load Balancers (ELB)**: Fetches ARNs of Load Balancers and retrieves associated tags.
- **ElastiCache**: Fetches cache cluster IDs, obtains their ARNs, and retrieves tags.
- **RDS Instances**: Fetches RDS instance ARNs and retrieves tags.
- **SQS Queues**: Lists queue URLs and retrieves their tags.
- **EC2 Instances**: Retrieves instance IDs and associated tags.
- **Database Insertion**: For each resource, the script extracts necessary details and inserts or updates them in the specified PostgreSQL table.

## Error Handling

- The script will print error messages if there are issues fetching tags or interacting with the database.
- Ensure your AWS credentials and database connection details are correct to avoid connection errors.

## Table Schema

The table `aws_resources` is created with the following columns:
- **id**: Primary key, auto-incremented.
- **customer_alias**: Formatted customer name (lowercase and no spaces).
- **customer_name**: The original customer name.
- **resource_type**: Type of the resource (e.g., `elb`, `ec2`, `sqs`, etc.).
- **resource_id**: ID of the resource.
- **UniqueConstraint**: Ensures uniqueness on the combination of `customer_alias` and `resource_id`.

## Contributing

Feel free to open issues or submit pull requests if you find bugs or have suggestions for improvements.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
Author: [@maks1mkin](https://github.com/maks1mkin)
-----------
