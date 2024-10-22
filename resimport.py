import boto3
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, text, UniqueConstraint  
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# AWS and DB configurations
customer_tag_key = input("Enter the AWS tag key for customer (e.g., 'customer'): ")
aws_regions = input("Enter AWS regions separated by commas (e.g., 'us-west-2,eu-central-1'): ")
db_url = input("Enter the database URL in the format 'postgresql+psycopg2://username:password@host:port/database_name': ")
table_name = input("Enter the name of the table to store the data (e.g., 'table_name'): ")

# Initialize SQLAlchemy
engine = create_engine(db_url)
metadata = MetaData()

# Define and create the table if it doesn't exist
resources_table = Table(table_name, metadata,
                        Column('id', Integer, primary_key=True, autoincrement=True),
                        Column('customer_alias', String(255)),
                        Column('customer_name', String(255)),
                        Column('resource_type', String(50)),
                        Column('resource_id', String(255)),
                        UniqueConstraint('customer_alias','resource_id', 'resource_type', name='uix_customer_resource'))
metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

def format_customer_alias(customer_name):
    """Format customer_alias: lower case and remove spaces."""
    return customer_name.lower().replace(' ', '')

def get_tags(client, resource_type, resource_id):
    """Retrieve tags for a resource."""
    try:
        if resource_type == 'elb':
            tags = client.describe_tags(ResourceArns=[resource_id])['TagDescriptions'][0]['Tags']
        elif resource_type == 'elasticache':
            tags = client.list_tags_for_resource(ResourceName=resource_id)['TagList']
        elif resource_type == 'rds':
            tags = client.list_tags_for_resource(ResourceName=resource_id)['TagList']
        elif resource_type == 'ec2':
            tags = client.describe_tags(Filters=[{'Name': 'resource-id', 'Values': [resource_id]}])['Tags']
        elif resource_type == 'sqs':
            tags = client.list_queue_tags(QueueUrl=resource_id)['Tags']
            tags = [{'Key': k, 'Value': v} for k, v in tags.items()]
        else:
            tags = []
    except Exception as e:
        print(f"Error retrieving tags for {resource_type} {resource_id}: {e}")
        tags = []
    return tags

def insert_to_db(customer_name, resource_id, resource_type):
    """Insert resource into the database."""
    # Check if customer_name or customer_alias is 'Unknown'
    if customer_name in [None, 'Unknown', 'Rallyware']:
        print(f"Skipping insertion for resource {resource_id} due to invalid customer name")
        return

    # Generate customer alias
    customer_alias = format_customer_alias(customer_name)
    if customer_alias in [None, 'Unknown','rallyware']:
        print(f"Skipping insertion for resource {resource_id} due to invalid customer alias")
        return

    # Prepare SQL statement
    sql_statement = text("""
        INSERT INTO aws_resources (customer_alias, customer_name, resource_type, resource_id)
        VALUES (:customer_alias, :customer_name, :resource_type, :resource_id)
        ON CONFLICT (customer_alias, resource_id, resource_type) DO UPDATE
            SET customer_name = EXCLUDED.customer_name,
                resource_type = EXCLUDED.resource_type
    """)

    try:
        # Execute SQL statement
        session.execute(sql_statement, {
            'customer_alias': customer_alias,
            'customer_name': customer_name,
            'resource_type': resource_type,
            'resource_id': resource_id
        })
        session.commit()
        print(f"Inserted/Updated resource: {resource_type} {resource_id} for customer {customer_name}")
    except SQLAlchemyError as e:
        session.rollback()
        print(f"SQLAlchemy Error: {e}")

def extract_resource_id(arn, resource_type):
    if resource_type == 'ec2':
        return arn.split(':instance/')[1]
    elif resource_type == 'elb':
        return arn.split('loadbalancer/')[1]
    elif resource_type == 'rds':
        return arn.split(':db:')[1]
    elif resource_type == 'elasticache':
        return arn.split(':cluster:')[1]
    elif resource_type == 'sqs':
         queue_name = arn.split('/')[-1]  # Extract the queue name from URL
         if '--' in queue_name:
            queue_name = queue_name.split('--')[0]
            return queue_name
    return arn

def process_region(region):
    """Process resources (ELB, RDS, ElastiCache, SQS, EC2) in a specific AWS region."""
    print(f"Processing region: {region}")

    # Process EC2 Instances
    ec2_client = boto3.client('ec2', region_name=region)
    instances = ec2_client.describe_instances().get('Reservations', [])
    for reservation in instances:
        for instance in reservation['Instances']:
            resource_id = instance['InstanceId']
            arn = f"arn:aws:ec2:{region}::{resource_id}"
            tags = get_tags(ec2_client, 'ec2', resource_id)
            customer_name = next((tag['Value'] for tag in tags if tag['Key'] == customer_tag_key), 'Unknown')
            insert_to_db(customer_name, resource_id, 'ec2')


    # Process Load Balancers (ELB)
    elbv2_client = boto3.client('elbv2', region_name=region)
    load_balancers = elbv2_client.describe_load_balancers().get('LoadBalancers', [])
    for lb in load_balancers:
        resource_id = extract_resource_id(lb['LoadBalancerArn'], 'elb')
        tags = get_tags(elbv2_client, 'elb', lb['LoadBalancerArn'])
        customer_name = next((tag['Value'] for tag in tags if tag['Key'] == customer_tag_key), 'Unknown')
        insert_to_db(customer_name, resource_id, 'elb')


    # Process RDS Instances
    rds_client = boto3.client('rds', region_name=region)
    db_instances = rds_client.describe_db_instances().get('DBInstances', [])
    for db_instance in db_instances:
        print(f"Processing RDS instance: {db_instance['DBInstanceIdentifier']}")   
        resource_id = extract_resource_id(db_instance['DBInstanceArn'], 'rds')
        tags = get_tags(rds_client, 'rds', db_instance['DBInstanceArn'])
        customer_name = next((tag['Value'] for tag in tags if tag['Key'] == customer_tag_key), 'Unknown')    
        insert_to_db(customer_name, resource_id, 'rds')
       

    # Process ElastiCache Clusters
    elasticache_client = boto3.client('elasticache', region_name=region)
    clusters = elasticache_client.describe_cache_clusters().get('CacheClusters', [])
    for cluster in clusters:
        cluster_id = cluster['CacheClusterId']
        arn = elasticache_client.describe_cache_clusters(CacheClusterId=cluster_id)['CacheClusters'][0]['ARN']
        tags = get_tags(elasticache_client, 'elasticache', arn)
        customer_name = next((tag['Value'] for tag in tags if tag['Key'] == customer_tag_key), 'Unknown')
        insert_to_db(customer_name, cluster_id, 'elasticache')


    # Process SQS Queues
    sqs_client = boto3.client('sqs', region_name=region)

    sqs_queues = sqs_client.list_queues().get('QueueUrls', [])

    print(f"Found {len(sqs_queues)} queues in region {region}")
    for queue_url in sqs_queues:
        queue_name = queue_url.split('/')[-1]
        tags = get_tags(sqs_client, 'sqs', queue_url)
        customer_name = next((tag['Value'] for tag in tags if tag['Key'] == customer_tag_key), None)
        if customer_name:
            sqs_prefix = queue_name.split('--')[0] if '--' in queue_name else queue_name
            insert_to_db(customer_name, sqs_prefix, 'sqs_prefix')
            print(f"Inserted queue {queue_name} with customer {customer_name} into the database.")
        else:
            print(f"No valid customer tag found for queue {queue_name}, skipping...")
 
def main():
    for region in aws_regions:
        process_region(region)

if __name__ == '__main__':
    main()
