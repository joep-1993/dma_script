"""
Test the exclusion logic fix on ad group 158342166366
"""
from google.ads.googleads.client import GoogleAdsClient
from dotenv import load_dotenv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from campaign_processor import rebuild_tree_with_custom_label_3_exclusion

load_dotenv()

credentials = {
    'developer_token': os.getenv('GOOGLE_ADS_DEVELOPER_TOKEN'),
    'client_id': os.getenv('GOOGLE_ADS_CLIENT_ID'),
    'client_secret': os.getenv('GOOGLE_ADS_CLIENT_SECRET'),
    'refresh_token': os.getenv('GOOGLE_ADS_REFRESH_TOKEN'),
    'use_proto_plus': True
}

login_customer_id = os.getenv('GOOGLE_ADS_LOGIN_CUSTOMER_ID')
if login_customer_id:
    credentials['login_customer_id'] = login_customer_id

client = GoogleAdsClient.load_from_dict(credentials)
customer_id = '3800751597'

ad_group_id = 158342166366
campaign_id = 21088950124
shop_to_exclude = '123inkt.nl'

print("=" * 80)
print("TESTING EXCLUSION FIX")
print("=" * 80)
print(f"Campaign ID: {campaign_id}")
print(f"Ad Group ID: {ad_group_id}")
print(f"Shop to exclude: {shop_to_exclude}")
print("=" * 80)

print("\nApplying exclusion...")
try:
    rebuild_tree_with_custom_label_3_exclusion(
        client=client,
        customer_id=customer_id,
        ad_group_id=ad_group_id,
        shop_name=shop_to_exclude,
        default_bid_micros=200000
    )
    print("\n✅ Exclusion applied successfully!")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "=" * 80)
print("Checking result...")
print("=" * 80)

import time
time.sleep(1)

# Check the result
ga_service = client.get_service('GoogleAdsService')
ag_service = client.get_service('AdGroupService')
ag_path = ag_service.ad_group_path(customer_id, ad_group_id)

query = f"""
    SELECT
        ad_group_criterion.resource_name,
        ad_group_criterion.listing_group.type,
        ad_group_criterion.listing_group.parent_ad_group_criterion,
        ad_group_criterion.listing_group.case_value.product_custom_attribute.index,
        ad_group_criterion.listing_group.case_value.product_custom_attribute.value,
        ad_group_criterion.negative,
        ad_group_criterion.cpc_bid_micros
    FROM ad_group_criterion
    WHERE ad_group_criterion.ad_group = '{ag_path}'
        AND ad_group_criterion.type = 'LISTING_GROUP'
"""

response = ga_service.search(customer_id=customer_id, query=query)

tree_nodes = []
for row in response:
    criterion = row.ad_group_criterion
    lg = criterion.listing_group

    node = {
        'resource': criterion.resource_name,
        'type': lg.type_.name,
        'parent': lg.parent_ad_group_criterion if lg.parent_ad_group_criterion else None,
        'negative': criterion.negative,
        'bid': criterion.cpc_bid_micros,
        'label_index': None,
        'label_value': None
    }

    if lg.case_value and lg.case_value._pb.WhichOneof("dimension") == "product_custom_attribute":
        node['label_index'] = lg.case_value.product_custom_attribute.index.name
        node['label_value'] = lg.case_value.product_custom_attribute.value if lg.case_value.product_custom_attribute.value else '(OTHERS)'

    tree_nodes.append(node)

root = next((n for n in tree_nodes if n['parent'] is None), None)

def print_tree(node, indent=0):
    """Print tree recursively"""
    indent_str = "  " * indent

    if node['parent'] is None:
        print(f"{indent_str}📁 ROOT (SUBDIVISION)")
    else:
        symbol = "🔀" if node['type'] == 'SUBDIVISION' else ("❌" if node['negative'] else "✅")
        label = f"{node['label_index']} = '{node['label_value']}'" if node['label_index'] else "UNKNOWN"
        type_info = node['type']
        neg_info = " [NEG]" if node['negative'] else " [POS]"
        bid_info = f" [Bid: {node['bid']/1000000:.2f}€]" if node['bid'] and node['bid'] > 0 else ""

        print(f"{indent_str}{symbol} {label} ({type_info}){neg_info}{bid_info}")

    children = [n for n in tree_nodes if n['parent'] == node['resource']]
    for child in children:
        print_tree(child, indent + 1)

print(f"\nFinal tree structure ({len(tree_nodes)} nodes):\n")
if root:
    print_tree(root)

print("\n" + "=" * 80)
print("VERIFICATION:")
print("=" * 80)
print("✅ Should have CL1 = 'a' subdivision")
print("✅ Should have CL0 = '9005157' subdivision (converted from unit)")
print("✅ Should have CL3 = '123inkt.nl' negative exclusion")
print("✅ Should preserve original structure and bid")
print("=" * 80)
