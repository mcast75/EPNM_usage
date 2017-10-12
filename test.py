#!/usr/bin/env python
__author__ = "Michael Castellana"
__email__ = "micastel@cisco.com"
__status__ = "Development"

#import necessary libraries
import base64, getpass, requests, json, sys, time
from epnm import EPNM
from time import sleep
import csv
from xlrd import open_workbook

SLOTS = []

with open("slotList.csv", 'r') as my_file:
    reader = csv.reader(my_file)
    for row in reader:
        SLOTS.append(row[0])
    print(SLOTS)

def get_headers(auth, content_type = "application", cache_control = "no-cache"):
    headers={
        'content-type': content_type,
        'authorization': "Basic "+ auth,
        'cache-control': cache_control,
    }
    return headers


def get_inventory(auth, host):
    """ Queries all registered Guests"""
    url = "https://"+host+"/webacs/api/v1/data/Devices.json?"
    headers = get_headers(auth)
    response = requests.request("GET", url, headers=headers, verify=False).json()
    response =  response['queryResponse']['entityId']
    id_list = []
    for item in response:
        id_list.append(str(item['$']))
    return id_list

def get_dev(auth, host, dev_id):
    url = "https://"+host+"/webacs/api/v1/data/InventoryDetails/"+dev_id+".json"
    headers = get_headers(auth)
    response = requests.request("GET", url, headers=headers, verify=False).json()
    dev_pair = {}
    print json.dumps(response, indent = 2)
    try:
        dev_type = str(response['queryResponse']['entity'][0]['devicesDTO'])
        dev_pair[dev_id] = dev_type
        return dev_pair
    except:
        return


def get_opt_dev(auth, host):
    response_list = []
    url = "https://"+host+"/webacs/api/v1/data/InventoryDetails.json?summary.productFamily=\"Optical Networking\"" 
    headers = get_headers(auth)
    response = requests.request("GET", url, headers=headers, verify=False).json()
    id_list = response['queryResponse']['entityId']
    for dev in id_list:
        response_list.append(str(dev['$']))
    return response_list

def get_NCS2K_dev(auth, host):
    response_list = []
    # url = "https://"+host+"/webacs/api/v1/data/InventoryDetails.json?summary.productFamily=\"Optical Networking\"" 
    # url = "https://"+host+"/webacs/api/v2/data/Devices.json?.full=true&deviceType=startsWith(\"Cisco NCS 2\")"
    # url = "https://"+host+"/webacs/api/v1/data/InventoryDetails.json?.full=true&summary.productFamily=\"Optical Networking\"&.maxResults=1"
    url = "https://"+host+"/webacs/api/v1/data/InventoryDetails.json?.full=true&summary.deviceType=startsWith(\"Cisco NCS 2\")&.maxResults=1"
    # display name matches ID and iPAddress matches Mike
    headers = get_headers(auth)
    response = requests.request("GET", url, headers=headers, verify=False).json()
    print json.dumps(response, indent = 2)
    # print response
    id_list = response['queryResponse']['entity']
    for dev in id_list:
        deviceID =  dev["devicesDTO"]["@displayName"]
        deviceIP =  dev["devicesDTO"]["ipAddress"]
        print deviceID
        print deviceIP
        response_list.append(str(deviceID))
    return response_list

def determineCapacity(deviceType):
    if deviceType == 'Cisco NCS 2006':
        return 8
    if deviceType == 'Cisco NCS 2015':
        return 17
    # if deviceType == 'Cisco NCS 2002':
    return 3

def createDeviceModel(deviceID, deviceIP, deviceName, deviceType, lineCards, slotUsage, capacity, utilization):
    device = {
        'deviceID' : deviceID,
        'deviceIP' : deviceIP,
        'deviceName' : deviceName,
        'deviceType' : deviceType,
        'lineCards' : lineCards,
        'slotUsage' : slotUsage,
        'capacity' : capacity,
        'utilization' : utilization
    }
    return device

def get_NCS2KMOD_dev(auth, host):
    response_list = []
    # url = "https://"+host+"/webacs/api/v1/data/InventoryDetails.json?summary.productFamily=\"Optical Networking\"" 
    # url = "https://"+host+"/webacs/api/v2/data/Devices.json?.full=true&deviceType=startsWith(\"Cisco NCS 2\")"
    # url = "https://"+host+"/webacs/api/v1/data/InventoryDetails.json?.full=true&summary.productFamily=\"Optical Networking\"&.maxResults=1"
    url = "https://"+host+"/webacs/api/v1/data/InventoryDetails.json?.full=true&summary.deviceType=startsWith(\"Cisco NCS 2\")&.maxResults=5"
    # display name matches ID and iPAddress matches Mike
    headers = get_headers(auth)
    response = requests.request("GET", url, headers=headers, verify=False).json()
    print json.dumps(response, indent = 2)
    # print response
    allDevices = []
    deviceList = response['queryResponse']['entity']

    for device in deviceList:
        summary = device['inventoryDetailsDTO']['summary']
        deviceID = summary['deviceId']
        deviceIP = summary['ipAddress']
        deviceName = summary['deviceName']
        deviceType = summary['deviceType']
        lineCards = {}
        slotUsage = 0
        capacity = determineCapacity(deviceType)
        modules = device['inventoryDetailsDTO']['modules']

        for module in modules['module']:
            productName = module["productName"]
            if productName in SLOTS:
                slotUsage += 1
                if productName in lineCards:
                    lineCards[productName] += 1
                else:
                    lineCards[productName] = 1

        utilization = float(slotUsage) / float(capacity)
        thisDevice = createDeviceModel(deviceID, deviceIP, deviceName, deviceType, lineCards, slotUsage, capacity, utilization)
        allDevices.append(thisDevice)

    for each in allDevices:
        for k in each:
            v = each[k]
            print v
        print
        print
    return allDevices

def get_ip_map(auth, host, id_list):
    opt_list = {}
    headers = get_headers(auth)
    for item in id_list:
        url = "https://"+host+"/webacs/api/v1/data/InventoryDetails/"+item+".json"
        response = requests.request("GET", url, headers=headers, verify=False).json()
        ip_addr = str(response['queryResponse']['entity'][0]['inventoryDetailsDTO']['summary']['ipAddress'])
        opt_list[item]=ip_addr

    return opt_list

def get_dev_det(auth, host,dev):
    inv_dets = {}
    
    url = "https://"+host+"/webacs/api/v1/data/InventoryDetails/"+dev+".json"
    headers = get_headers(auth)
    response = requests.request("GET", url, headers=headers, verify=False).json()
    # print json.dumps(response['queryResponse']['entity'][0]['inventoryDetailsDTO']['modules']['module'], indent=2)
    # print len(response['queryResponse']['entity'][0]['inventoryDetailsDTO']['modules']['module'])
    dev_type = response['queryResponse']['entity'][0]['inventoryDetailsDTO']['summary']['deviceType']
    mod_list = response['queryResponse']['entity'][0]['inventoryDetailsDTO']['modules']['module']
    i = 0
    for item in mod_list:
        r_list = []
        if item['equipmentType'] == 'MODULE': #and item['physicalLocation'] == 'SHELF':
            # print json.dumps(item, indent=2)

            i = i+1
            r_list.append(str(dev_type))
            r_list.append(str(item['productName']))

            try:
                r_list.append(str(item['description']))
            except:
                r_list.append(str('No Description Listed'))
            
            try:
                r_list.append(str(item['physicalLocation']))
            except:
                r_list.append(str('No Location Listed'))

        
            inv_key = dev+' ['+str(i)+']'
            inv_dets[inv_key] = r_list

    # print '\n-------------------------'
    # print str(i) + " Modules"
    # print '-------------------------\n'

    return inv_dets

    # print json.dumps(response['queryResponse']['entity'][0]['inventoryDetailsDTO']['udiDetails'], indent=2)

if __name__ == '__main__':
    #Disable warnings since we are not verifying SSL
    requests.packages.urllib3.disable_warnings()
    host_addr = 'tme-epnm'
    # user = raw_input("User: ")
    # pwd = getpass.getpass("Password: ")

    #use above for taking in arguments- i got lazy so i didnt feel like typing it each time
    #i just took the commands at run time
    user = sys.argv[1]
    pwd = sys.argv[2]
    auth = base64.b64encode(user + ":" + pwd)


    #id_ip_map = get_ip_map(auth, host_addr, get_opt_dev(auth, host_addr))
    
    # for k in id_ip_map:
    #   v = id_ip_map[k]
    #   print (k, v)

    deviceList = get_dev(auth, host_addr, "7688694")

    ref_out = '2k.csv'
    with open(ref_out, 'w') as output:
        fieldnames = ['deviceID', 'deviceIP', 'deviceName', 'deviceType', 'lineCards', 'slotUsage', 'capacity', 'utilization']
        out_writer = csv.DictWriter(output, fieldnames=fieldnames)
        out_writer.writerow({'deviceID': 'Device ID', 'deviceIP':'Device IP', 'deviceName':'Device Name', 'deviceType':'Device Type', 'lineCards':'Line Cards', 'slotUsage':'Slot Usage', 'capacity':'Capacity', 'utilization':'Utilization'})
        for device in deviceList:
            out_writer.writerow({'deviceID':device['deviceID'], 'deviceIP':device['deviceIP'], 'deviceName':device['deviceName'],'deviceType':device['deviceType'], 'lineCards':device['lineCards'], 'slotUsage':device['slotUsage'], 'capacity':device['capacity'], 'utilization':device['utilization']})


    