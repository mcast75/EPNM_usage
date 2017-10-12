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

def get_response(url, headers, requestType = "GET", verify = False):
    return requests.request(requestType, url, headers=headers, verify = verify).json()

def get_device_ID_list(response):
    id_list = []
    for item in response:
        id_list.append(str(item['$']))
    return id_list


def get_inventory(auth, host):
    """ Queries all registered Guests"""
    url = "https://"+host+"/webacs/api/v1/data/Devices.json?"
    headers = get_headers(auth)
    response = get_response(url, headers, requestType = "GET", verify = False)
    response =  response['queryResponse']['entityId']
    id_list = get_device_ID_list(response)
    return id_list

def get_single_device(auth, host, dev_id):
    url = "https://"+host+"/webacs/api/v1/data/InventoryDetails/"+dev_id+".json"
    headers = get_headers(auth)
    response = get_response(url, headers, requestType = "GET", verify = False)
    dev_pair = {}
    try:
        dev_type = str(response['queryResponse']['entity'][0]['inventoryDetailsDTO'])
        dev_pair[dev_id] = dev_type
        return dev_pair
    except:
        raise ValueError("Device " + str(dev_id) + " not found")

def get_all_optical_device_ids(auth, host):
    url = "https://"+host+"/webacs/api/v1/data/InventoryDetails.json?summary.productFamily=\"Optical Networking\"" 
    headers = get_headers(auth)
    response = get_response(url, headers, requestType = "GET", verify = False)
    response =  response['queryResponse']['entityId']
    id_list = get_device_ID_list(response)
    return id_list

def determineTotalCapacity(physicalLocation):
    if physicalLocation == 'SHELF':
        return 8
    location = physicalLocation[0:6]
    if 'SHELF-' == location:
        productFamily = physicalLocation[-4:]
        if '-M2]' == productFamily:
            return 3
        if '-M6]' == productFamily:
            return 8
        if 'M15]' == productFamily:
            return 17
        raise ValueError("SHELF")
    if 'PSHELF' == location:
        productFamily = physicalLocation[-5:]
        if '-2RU]' == productFamily:
            return 3
        if '-6RU]' == productFamily:
            return 8
        if '-15RU]' == productFamily:
            return 17
        raise ValueError("PHSELF")
    return 0

def createDeviceModel(deviceID, deviceIP, deviceName, deviceType, lineCards, slotUsage, capacity, chassisCapacity, utilization):
    device = {
        'deviceID' : deviceID,
        'deviceIP' : deviceIP,
        'deviceName' : deviceName,
        'deviceType' : deviceType,
        'lineCards' : lineCards,
        'slotUsage' : slotUsage,
        'capacity' : capacity,
        'chassisCapacity' : chassisCapacity,
        'utilization' : utilization
    }
    return device

def get_NCS2KMOD_dev(auth, host):
    response_list = []
    # url = "https://"+host+"/webacs/api/v1/data/InventoryDetails.json?summary.productFamily=\"Optical Networking\"" 
    # url = "https://"+host+"/webacs/api/v2/data/Devices.json?.full=true&deviceType=startsWith(\"Cisco NCS 2\")"
    # url = "https://"+host+"/webacs/api/v1/data/InventoryDetails.json?.full=true&summary.productFamily=\"Optical Networking\"&.maxResults=1"
    url = "https://"+host+"/webacs/api/v1/data/InventoryDetails.json?.full=true&summary.deviceType=startsWith(\"Cisco NCS 2\")"
    # display name matches ID and iPAddress matches Mike
    headers = get_headers(auth)
    response = get_response(url, headers, requestType = "GET", verify = False)
    # print json.dumps(response, indent = 2)
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
        chasses = []
        slotUsage = 0
        capacity = determineCapacity(deviceType)
        chassisCapacity = 0
        modules = device['inventoryDetailsDTO']['modules']

        for module in modules['module']:
            productName = module["productName"]
            if productName in SLOTS:
                slotUsage += 1
                if productName in lineCards:
                    lineCards[productName] += 1
                else:
                    lineCards[productName] = 1

            if "physicalLocation" in module:
                physicalLocation = module["physicalLocation"]
                if physicalLocation in chasses:
                    print "Already counted" + physicalLocation
                else:
                    extraChassisCapacity = determineTotalCapacity(physicalLocation)
                    if extraChassisCapacity > 0:
                        chassisCapacity += extraChassisCapacity
                        chasses.append(physicalLocation)



        # fans = device['inventoryDetailsDTO']['fans']
        # print fans
        # print fans['fan']
        # if type(fans['fan']) is list:
        #     for fan in fans['fan']:
        #         fanName = fan['name']
        #         print fanName
        #         print "LISTSTSTST"
        #         fanCapacity += determineFanCapacity(fanName)
        # if type(fans['fan']) is dict:
        #     fanName = fans['fan']['name']
        #     print fanName
        #     print "DICTCISODJFOSDJFIOSDF"
        #     fanCapacity += determineFanCapacity(fanName)
        

        utilization = float(slotUsage) / float(capacity)
        thisDevice = createDeviceModel(deviceID, deviceIP, deviceName, deviceType, lineCards, slotUsage, capacity, chassisCapacity, utilization)
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
        response = get_response(url, headers, requestType = "GET", verify = False)
        ip_addr = str(response['queryResponse']['entity'][0]['inventoryDetailsDTO']['summary']['ipAddress'])
        opt_list[item]=ip_addr

    return opt_list

def get_dev_det(auth, host,dev):
    inv_dets = {}
    
    url = "https://"+host+"/webacs/api/v1/data/InventoryDetails/"+dev+".json"
    headers = get_headers(auth)
    response = get_response(url, headers, requestType = "GET", verify = False)
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

    # print get_single_device(auth, host_addr, "7688707")
    print get_all_optical_device_ids(auth, host_addr)
    # deviceList = get_NCS2KMOD_dev(auth, host_addr)

    # ref_out = '2k.csv'
    # with open(ref_out, 'w') as output:
    #     fieldnames = ['deviceID', 'deviceIP', 'deviceName', 'deviceType', 'lineCards', 'slotUsage', 'capacity', 'chassisCapacity', 'utilization']
    #     out_writer = csv.DictWriter(output, fieldnames=fieldnames)
    #     out_writer.writerow({'deviceID': 'Device ID', 'deviceIP':'Device IP', 'deviceName':'Device Name', 'deviceType':'Device Type', 'lineCards':'Line Cards', 'slotUsage':'Slot Usage', 'capacity':'Capacity', 'chassisCapacity':'Chassis Capacity', 'utilization':'Utilization'})
    #     for device in deviceList:
    #         out_writer.writerow({'deviceID':device['deviceID'], 'deviceIP':device['deviceIP'], 'deviceName':device['deviceName'],'deviceType':device['deviceType'], 'lineCards':device['lineCards'], 'slotUsage':device['slotUsage'], 'capacity':device['capacity'], 'chassisCapacity':device['chassisCapacity'], 'utilization':device['utilization']})


    