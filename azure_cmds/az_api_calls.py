import os
from azure.identity import ClientSecretCredential 
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.compute.models import DiskCreateOption, DiskCreateOptionTypes, Image, SubResource, VirtualMachineSizeTypes, NetworkInterfaceReference, VirtualMachine, StorageProfile, HardwareProfile, NetworkProfile
from azure.core.exceptions import ResourceNotFoundError, ClientAuthenticationError
from pprint import pprint
import datetime
import time

# az login
# az ad sp create-for-rbac --name localtest-sp-rbac --sdk-auth > local-sp.json
# populate from json and set environment variables
os.environ['AZURE_CLIENT_ID']= "example-client-id"
os.environ['AZURE_CLIENT_SECRET']= "example-client-secret"
os.environ['AZURE_TENANT_ID'] ="example-tenant-id"


subscription_id = os.environ.get(
    'AZURE_SUBSCRIPTION_ID',
    'example-subscription')

az_credentials = ClientSecretCredential(
    tenant_id=os.getenv('AZURE_TENANT_ID'),
    client_id=os.getenv('AZURE_CLIENT_ID'),
    client_secret=os.getenv('AZURE_CLIENT_SECRET')
)

client = ResourceManagementClient(az_credentials,subscription_id)
network_client = NetworkManagementClient(az_credentials,subscription_id)
# possibly equivalent with boto3.client('ec2')
compute_client = ComputeManagementClient(az_credentials,subscription_id)

location='westus2'
resource_group_params = {'location':location}

test_group_name="test01_group"

#tested
def get_item_attrs(item):
    # for additional object info
    for attr in dir(item): 
        print(attr +'()') if callable(getattr(item, attr)) else print(attr)

# tested
# list resource group
def list_resource_groups():
    rg_list=client.resource_groups.list()
    new_rg_list=[]
    for item in rg_list:
        new_rg_list.append(item.as_dict())
    return new_rg_list
        # for additional object info
        #for attr in dir(item): 
        #    print(attr +'()') if callable(getattr(item, attr)) else print(attr)

# create a resource group
def create_resource_group(group_name):
    client.resource_groups.create_or_update(group_name, resource_group_params)

# update a resource group
def update_resource_group(group_name):
    resource_group_params.update(tags={'hello': 'world'})
    client.resource_groups.create_or_update(group_name, resource_group_params)

#tested
# list resource within group
def list_resource_groups_resources(group_name):
    for item in client.resources.list_by_resource_group(group_name):
        pprint(item.as_dict())

# export the resource group template
def export_resource_group_template(group_name):
    client.resource_groups.export_template(group_name, ['*'])

# Delete the resource group
def delete_resource_group(group_name):
    delete_async_operation = client.resource_groups.begin_delete(group_name)
    delete_async_operation.wait()

#tested
# get vm status or state
def get_vm_status(resource_group_name, vm_name):
    try:
        return compute_client.virtual_machines.get(resource_group_name, vm_name, expand='instanceView').instance_view.statuses[1].display_status
    except:
        return "VM terminated"

# tested
# tag is name
def is_instance_running(instance_tag):
    status=get_vm_status(test_group_name,instance_tag)
    if status == "VM running":
        return True
    else:
        return False

#tested
def is_instance_stopped(instance_tag):
    # get_vm_status compare to running return true or false
    status=get_vm_status(test_group_name,instance_tag)
    if status == "VM deallocated" or status == "VM stopped":
        return True
    else:
        return False

#tested
def is_instance_terminated(instance_tag):
    if status == "VM terminated":
        return True
    else:
        return False

#tested
# rename detach_ebs_stop_instance
def detach_drive_stop_instance(instance_tag):
    #instance_tag should be vm_name
    # group_name should come from environment variable
    vm = compute_client.virtual_machines.get(
            test_group_name,
            instance_tag)
    vm = detach_datadisk(vm,test_group_name,instance_tag)
    stop_single_instance(instance_tag)

#tested
def detach_datadisk(vm,group_name,vm_name):
    data_disks = vm.storage_profile.data_disks
    data_disks[:] = [
        disk for disk in data_disks if disk.name != 'mydatadisk1']
    async_vm_update = compute_client.virtual_machines.begin_create_or_update(
        group_name,
        vm_name,
        vm
    )
    #async_vm_update.wait()
    return async_vm_update.result()

#tested
def stop_single_instance(instance_tag):
    # group_name should come from environment variable
    async_stop = compute_client.virtual_machines.begin_deallocate(test_group_name, instance_tag)
    async_stop.wait()


# Theory is that vm names are the equivalent of instance ids in aws, otherwise 
# instances must be in a scale set to use an id. Virtual machines in Azure have 
# two distinct names: virtual machine name, and host name.
def stop_instances(instance_ids):
    # assuming ids can be used as tags
    for instance_tag in instance_ids:
        stop_single_instance(instance_tag)

#tested
def start_single_instance(instance_tag):
    # group_name should come from environment variable
    async_start= compute_client.virtual_machines.begin_start(test_group_name, instance_tag)
    async_start.wait()

def start_instances(instance_ids):
    # assuming ids can be used as tags
    for instance_tag in instance_ids:
        start_single_instance(instance_tag)

# tested
# vm_size in Azure is the equivalent of instance_type in AWS
def modify_instance_types(instance_id,instance_type):
    """
       e.g
       - Standard_D2s_v3
       - Standard_DS2_v2
    """
    # group_name should come from environment variable
    vm = compute_client.virtual_machines.get(test_group_name, instance_id)
    vm.hardware_profile.vm_size = instance_type
    update_result = compute_client.virtual_machines.begin_create_or_update(
        test_group_name, 
        instance_id, 
        vm
    )
    return update_result

#tested
def get_instance_from_id(instance_id):
    try:
        return compute_client.virtual_machines.get(test_group_name, instance_id)
    except DataNotFoundError as e:
        #logging.error(e)
        return None

# tested
def get_instance_type(instance_id):
    try:
        inst = get_instance_from_id(instance_id)
        inst_dict=inst.as_dict()
        return inst_dict['hardware_profile']['vm_size']
    except:
        return "Null"

def get_instances():
    try:
        return compute_client.virtual_machines.list_all()
    except DataNotFoundError as e:
        # logging.error(e)
        return None

# tested
#placeholder so backends match till refactoring
def get_eip_allocation_id(instance_id):
    return get_public_ip_name(instance_id)

#tested
# equivalent get_eip_allocation_id
# possibly allocation id is just a name for a known public ip
# https://docs.microsoft.com/en-us/azure/virtual-network/public-ip-addresses
def get_public_ip_name(instance_id):
    net_id=compute_client.virtual_machines.get(test_group_name, instance_id).as_dict()['network_profile']['network_interfaces'][0]['id']
    net_infs=network_client.network_interfaces.list(test_group_name)
    ip_id=""
    for net_inf in net_infs:
        if net_inf.as_dict()['id']==net_id:
            ip_id=net_inf.as_dict()['ip_configurations'][0]['public_ip_address']['id']
    if ip_id:
        ips=network_client.public_ip_addresses.list(test_group_name)
        for ip_a in ips:
            ip_b=ip_a.as_dict()
            if ip_b['id']==ip_id:
                return ip_b['name']
    return "None"

#tested
def get_private_ip_address(instance_id):
    net_id=compute_client.virtual_machines.get(test_group_name, instance_id).as_dict()['network_profile']['network_interfaces'][0]['id']
    net_infs=network_client.network_interfaces.list(test_group_name)
    for net_inf in net_infs:
        if net_inf.as_dict()['id']==net_id:
            return net_inf.as_dict()['ip_configurations'][0]['private_ip_address']
    return "Address Not Found"

#tested
def create_static_ip(ip_name):
    ip_params={
               'location':location,
               "publicIPAllocationMethod": "Static",
               'public_ip_address_version':'ipv4'
              }
    network_client.public_ip_addresses.begin_create_or_update(test_group_name,ip_name,ip_params)
    return "Done"

# tested
# equivalent associate_eip_allocation_id
# allocation ids is just a tag name
def associate_public_ip_name(instance_id,tag_name):
    net_id=compute_client.virtual_machines.get(test_group_name, instance_id).as_dict()['network_profile']['network_interfaces'][0]['id']
    net_infs=network_client.network_interfaces.list(test_group_name)
    net_name=""
    for net_inf in net_infs:
        if net_inf.as_dict()['id']==net_id:
            net_name=net_inf.as_dict()['name']
    net_params={'location':location,
                'ipConfigurations': [
                        {
                        "name": "ipconfig1",
                        "properties": {
                            "privateIpAddressVersion": "IPv4",
                            "privateIPAllocationMethod": "Dynamic",
                            "publicIPAddress": {
                                "id": "/subscriptions/"+subscription_id+"/resourceGroups/"+test_group_name+"/providers/Microsoft.Network/publicIPAddresses/"+tag_name
                            },
                            "subnet": {
                                "id": "/subscriptions/"+subscription_id+"/resourceGroups/"+test_group_name+"/providers/Microsoft.Network/virtualNetworks/"+test_group_name+"-vnet/subnets/default"
                            }
                        }
                    }
                ]
                }
    network_client.network_interfaces.begin_create_or_update(test_group_name, net_name,net_params)

#tested
def terminate_instances(instance_ids):
    # assuming ids can be used as tags
    for instance_tag in instance_ids:
        stop_single_instance(instance_tag)
        async_vm_delete = compute_client.virtual_machines.begin_delete(test_group_name, instance_tag)
        async_vm_delete.wait()
        print("vm deleted")

#tested
# takes a private ip and returns a machine name
def gather_id_list(node_ip):
    vm_list=compute_client.virtual_machines.list(test_group_name)
    node_id_ip=[]
    for vm in vm_list:
        priv_ip=get_private_ip_address(vm.as_dict()["name"])
        if node_ip==priv_ip:
            node_id_ip.append((vm.as_dict()["name"],node_ip))
    return node_id_ip


#tested
def list_vnets(rg_name):
    vn_list=network_client.virtual_networks.list(rg_name)
    new_vn_list=[]
    for item in vn_list:
        new_vn_list.append(item.as_dict())
    return new_vn_list

# tested
def create_virtual_network(vn_name):
    vn_params = {
                 "location":location,
                 "properties": {
                     "addressSpace": {
                         "addressPrefixes": [
                             "10.0.0.0/16"
                          ]
                      },
                      "subnets": [{
                          "name": "default",
                          "id": "/subscriptions/"+subscription_id+"/resourceGroups/"+vn_name+"/providers/Microsoft.Network/virtualNetworks/"+vn_name+"-vnet/subnets/default",
                          "properties": {
                              "addressPrefix": "10.0.0.0/24"
                          },
                          "type": "Microsoft.Network/virtualNetworks/subnets"
                      }]
                  }
                }
    network_client.virtual_networks.begin_create_or_update(vn_name, vn_name+"-vnet",vn_params)

#tested
def ensure_virtual_network(vn_name):
    vn_list=list_vnets(vn_name)
    for vn in vn_list:
        if vn["name"] == vn_name+"-net":
            return
    print("virtual network needs to be created")
    create_virtual_network(vn_name)

# tested
def ensure_resource_group(rg_name):
    rg_list=list_resource_groups()
    for rg in rg_list:
        if rg["name"] == rg_name:
            return
    print("resource group needs to be created")
    create_resource_group(rg_name)

# tested
def create_snapshot_from_volume(volume_id,snapshot_desc):
    managed_disk = compute_client.disks.get(test_group_name, volume_id)
    snapshot_name = "snapshot_"+(str(datetime.datetime.now().time())).replace(":","").replace(".","")
    async_snapshot_creation = compute_client.snapshots.begin_create_or_update(
            test_group_name,
            snapshot_name,
            {
                'location': location,
                'creation_data': {
                    'create_option': 'Copy',
                    'source_uri': managed_disk.id
                },
                'tags': {
                    'description': snapshot_desc
                }
            }
        )
    #snapshot = async_snapshot_creation.result()
    return snapshot_name
      
#tested
# publishing images in azure is different
#https://medium.com/spectro-cloud/custom-vm-images-on-azure-4382c9393d8d
#https://docs.microsoft.com/en-us/python/api/azure-mgmt-compute/azure.mgmt.compute.v2020_09_30.models.galleryimage?view=azure-python
#https://stackoverflow.com/questions/33271570/how-to-create-a-vm-with-a-custom-image-using-azure-sdk-for-python
def register_image_from_snapshot(root_snapshot_id,root_device,home_snapshot_id,home_device,mi_name):
    ensure_resource_group(test_group_name)
    print("2 minute delay")
    time.sleep(120)
    ensure_virtual_network(test_group_name)
    print("2 minute delay")
    time.sleep(120)
    nic_name="nic_"+(str(datetime.datetime.now().time())).replace(":","").replace(".","")
    nic_params={'location':location,
                'ipConfigurations': [
                        {
                        "name": "ipconfig1",
                        "properties": {
                            "privateIpAddressVersion": "IPv4",
                            "privateIPAllocationMethod": "Dynamic",
                            "subnet": {
                                "id": "/subscriptions/"+subscription_id+"/resourceGroups/"+test_group_name+"/providers/Microsoft.Network/virtualNetworks/"+test_group_name+"-vnet/subnets/default"
                            }
                        }
                    }
                ]
                }
    network_client.network_interfaces.begin_create_or_update(test_group_name, nic_name, nic_params)
    
    root_snapshot = compute_client.snapshots.get(test_group_name, root_snapshot_id)

    compute_client.disks.begin_create_or_update(
        test_group_name,
        root_device,
        {
            'location': location,
            'creation_data': {
                'create_option': DiskCreateOption.copy,
                'source_resource_id': root_snapshot.id
            }
        }
    )

    home_snapshot = compute_client.snapshots.get(test_group_name, home_snapshot_id)

    compute_client.disks.begin_create_or_update(
        test_group_name,
        home_device,
        {
            'location': location,
            'creation_data': {
                'create_option': DiskCreateOption.copy,
                'source_resource_id': home_snapshot.id
            }
        }
    )

    print("5 minute delay")
    time.sleep(300)
    print("Create vm")
    os_disk = compute_client.disks.get(test_group_name, root_device)
    home_disk = compute_client.disks.get(test_group_name, home_device)
    net_interface=network_client.network_interfaces.get(test_group_name,nic_name)

    hp = HardwareProfile(vm_size='Standard_DS2_v2')
    compute_client.virtual_machines.begin_create_or_update(
        test_group_name,
        mi_name,
        VirtualMachine(
            location=location,
            name=mi_name,
            hardware_profile=hp,
            network_profile=NetworkProfile(
                network_interfaces=[
                    {
                        'id': net_interface.id
                    }
                ],
            ),
            storage_profile=StorageProfile(
                os_disk={    
                    'os_type': "Linux",
                    'name': os_disk.name,
                    'create_option': DiskCreateOptionTypes.attach,
                    'managed_disk': {
                        'id': os_disk.id
                    }
                },
                data_disks=[{    
                    'lun': 0, 
                    'name': home_disk.name,
                    'create_option': DiskCreateOptionTypes.attach,
                    'managed_disk': {
                        'id': home_disk.id
                    }
                }]
            ),
        ),
    )
    print("2 minute delay")
    time.sleep(180)
    print("Create vm image")
    create_image_from_vm(mi_name)
    print("2 minute delay")
    time.sleep(180)
    # delete vm
    compute_client.virtual_machines.begin_delete(test_group_name,mi_name)
    print("2 minute delay")
    time.sleep(180)
    # delete disk
    compute_client.disks.begin_delete(test_group_name,home_device)
    compute_client.disks.begin_delete(test_group_name,root_device)
    # delete nic
    network_client.network_interfaces.begin_delete(test_group_name, nic_name)
      
# tested
def wait_for_snapshots(snapshot_ids):
    for snapshot_id in snapshot_ids:
        wait_for_snapshot_helper(snapshot_id)
    print("Done")

#tested
def wait_for_snapshot_helper(snapshot_id):
    cnt=0
    while cnt < 50:
        snapshot_value = compute_client.snapshots.get(test_group_name,snapshot_id)
        state=snapshot_value.provisioning_state
        print(state)
        if state == "Succeeded":
            return "Success"
        cnt=cnt+1
        time.sleep(5)
    return "Failure"
      

# tested
def delete_snapshots(snapshot_ids):
    for snapshot_id in snapshot_ids:
        delete_snapshot_helper(snapshot_id)

#tested
def delete_snapshot_helper(snapshot_id):
    mi=compute_client.snapshots.begin_delete(test_group_name,snapshot_id)
    return "ImageDeleted"
      
# tested       
def wait_for_image(image_id):
    try:
        cnt=0
        while cnt < 50:
            img_value = compute_client.images.get(test_group_name,image_id)
            state=img_value.provisioning_state
            if state == "Succeeded":
                return "Success"
            cnt=cnt+1
            time.sleep(5)
        return "Failure"
    except:
        return "Error"

# tested - use for testing
def create_image_from_vm(vm_name):
    # Deallocate
    async_vm_deallocate = compute_client.virtual_machines.begin_deallocate(test_group_name, vm_name)
    async_vm_deallocate.wait()

    # Generalize (possible because deallocated)
    compute_client.virtual_machines.generalize(test_group_name, vm_name)

    vm = compute_client.virtual_machines.get(test_group_name, vm_name)
    sub_resource = SubResource(id=vm.id)
    params = Image(location=location, source_virtual_machine=sub_resource)
    img_name = "vm_image_"+(str(datetime.datetime.now().time())).replace(":","").replace(".","")
    compute_client.images.begin_create_or_update(
        test_group_name,
        img_name,
        params
    )
    return img_name
    #image = async_create_image.result()

#tested
def delete_image_by_id(image_id):
    try:
        mi=compute_client.images.begin_delete(test_group_name,image_id)
        return "ImageDeleted"
    except:
        return "FailedToDeleteImage"
      
# tested
def wait_for_volume(volume_id,state,timeout_seconds):
    try:
        found_state = False
        vol=compute_client.disks.get(test_group_name, volume_id)
        stop_time = time.time()+timeout_seconds
        #get_item_attrs(vol) 
        while True:
            vol_state = vol.disk_state
            # 'Unattached', 'Attached'
            pprint(vol_state)
            if vol_state == state:
                found_state = True
                break;
            if time.time() > stop_time:
                break;
            time.sleep(5)
        return found_state
    except:
        #logging.error(e)
        return "Failed to retrieve state"

#tested
def delete_volume_by_id(volume_id):
    compute_client.disks.begin_delete(test_group_name,volume_id)


#tested
# equivalent of create_ebs
# drives have a unique name and a unique id
def create_drive(az,size):
    temp_name = "temp_"+(str(datetime.datetime.now().time())).replace(":","").replace(".","")
    create_named_drive(az,size,temp_name)
    return temp_name

#tested
def create_named_drive(az,size,disk_name):

    poller = compute_client.disks.begin_create_or_update(
        test_group_name,
        disk_name,
        {
            'location': location,
            'disk_size_gb': size,
            'creation_data': {
                'create_option': DiskCreateOption.empty
            }
        }
    )
    return poller.result()
    
# tested      
# equivalent of set_ebs_name
def set_drive_name(volume_id,name_value): 
    try:
        disk_drive=compute_client.disks.get(test_group_name, volume_id)
        print("get fine")
        disk_drive.tags['Name']=name_value
        print("tag fine")
        poller = compute_client.disks.begin_create_or_update(
            test_group_name,
            disk_drive.name,
            disk_drive    
        )

        poller.result()
        print("done")
        return True
    except ResourceNotFoundError as rnfe:
        #log error
        print("Resource not found")
        return False
    except ClientAuthenticationError as e:
        #log error
        return "InvalidCredentials"

#tested
# equivalent of ebs_tag_exists
def drive_tag_exists(az,tag_name):
    try:
        compute_client.disks.get(test_group_name, tag_name)
        return True
    except ResourceNotFoundError as rnfe:
        return False
    except ClientAuthenticationError as e:
        #log error
        return "InvalidCredentials"

#def locate_value(a_dict,value):
#make dictionary a list, iterate to check if value is present.


def main():
    """
    print("Creating group test")
    create_resource_group("test01")
    list_resource_groups()
    print("Deleting group test")
    delete_resource_group("test01")
    list_resource_groups()

    status = get_vm_status(test_group_name,"test01")
    pprint(status)
    stop_single_instance("test01")
    if is_instance_stopped("test01"):
        print("instance is stopped")
    status = get_vm_status(test_group_name,"test01")
    pprint(status)
    start_single_instance("test01")
    if is_instance_running("test01"):
        print("instance is running")
    status = get_vm_status(test_group_name,"test01")
    pprint(status)
    
    terminate_instances(["test01"])
    status = get_vm_status(test_group_name,"test01")
    pprint(status)

    get_item_attrs(compute_client.virtual_machines)
    detach_drive_stop_instance("test01")
    get_item_attrs(client.resource_groups)
    list_resource_groups_resources(test_group_name)

    inst = get_instance_from_id("test01")
    pprint(inst.as_dict())
    #Standard_DS2_v2
    #Standard_D2s_v3
    print(get_instance_type("test01"))
    pprint(modify_instance_types("test01","Standard_DS2_v2"))
    print(get_instance_type("test01"))

    result = drive_tag_exists('dummmy01','test01_disk1_587ab335e575455cb318b3dff746df8e')
    pprint(result)

    set_drive_name("test01_disk1_587ab335e575455cb318b3dff746df8e","test002")
    
    create_drive("",20)
    delete_volume_by_id("temp_215901.467186")
    print(wait_for_volume("test01_DataDisk_0","",10))
    print(delete_image_by_id("test01-image-20210203140149"))
    
    vm_image=create_image_from_vm("test01")
    pprint(wait_for_image(vm_image))
    snapshot_ids=[]
    for i in range(0,3):
        print(i)
        snapshot_ids.append(create_snapshot_from_volume("test01_disk1_f09f05df71944ad7911887e138b22d8f","dummy description about a whole bunch of things"))
    pprint(snapshot_ids)
    time.sleep(45)
    delete_snapshots(snapshot_ids)
    
    root_snapshot_id="snapshot_root002"
    root_device="root002"
    home_snapshot_id="snapshot_home001"
    home_device="home002"
    mi_name="test002"
    #get_item_attrs(network_client.virtual_networks)
    #ensure_virtual_network(test_group_name)
    register_image_from_snapshot(root_snapshot_id,root_device,home_snapshot_id,home_device,mi_name)
    
    print(get_eip_allocation_id('test01'))
    
    vm_name='test01'
    ip_name='static_test01-ip'
    associate_public_ip_name(vm_name,ip_name)
    ip_addr='10.0.0.4'
    pprint(gather_id_list(ip_addr))
    """
    print(create_static_ip("static_test02-ip"))    


if __name__ == "__main__":
    main()
