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


def get_inventory(auth, host):
	""" Queries all registered Guests"""
	url = "https://"+host+"/webacs/api/v1/data/Devices.json?"
	headers={
		'content-type': "application",
    	'authorization': "Basic "+auth,
    	'cache-control': "no-cache",
	}
	response = requests.request("GET", url, headers=headers, verify=False).json()
	response =  response['queryResponse']['entityId']
	id_list = []
	for item in response:
		id_list.append(str(item['$']))
	return id_list

def get_dev(auth, host, dev_id):
	url = "https://"+host+"/webacs/api/v1/data/Devices/"+dev_id+".json"
	headers={
		'content-type': "application",
    	'authorization': "Basic "+auth,
    	'cache-control': "no-cache",
	}
	response = requests.request("GET", url, headers=headers, verify=False).json()
	dev_pair = {}

	try:
		dev_type = str(response['queryResponse']['entity'][0]['devicesDTO'])
		dev_pair[dev_id] = dev_type
		return dev_pair
	except:
		return


def get_opt_dev(auth, host):
	response_list = []
	url = "https://"+host+"/webacs/api/v1/data/InventoryDetails.json?summary.productFamily=\"Optical Networking\"" 
	headers={
		'content-type': "application",
    	'authorization': "Basic "+auth,
    	'cache-control': "no-cache",
	}
	response = requests.request("GET", url, headers=headers, verify=False).json()
	id_list = response['queryResponse']['entityId']
	for dev in id_list:
		response_list.append(str(dev['$']))

	return response_list


def get_ip_map(auth, host, id_list):
	opt_list = {}

	headers={
		'content-type': "application",
    	'authorization': "Basic "+auth,
    	'cache-control': "no-cache",
	}
	for item in id_list:
		url = "https://"+host+"/webacs/api/v1/data/InventoryDetails/"+item+".json"
		response = requests.request("GET", url, headers=headers, verify=False).json()
		ip_addr = str(response['queryResponse']['entity'][0]['inventoryDetailsDTO']['summary']['ipAddress'])
		opt_list[item]=ip_addr

	return opt_list

def get_dev_det(auth, host,dev):
	inv_dets = {}
	
	url = "https://"+host+"/webacs/api/v1/data/InventoryDetails/"+dev+".json"
	headers={
		'content-type': "application",
    	'authorization': "Basic "+auth,
    	'cache-control': "no-cache",
	}
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
	# 	v = id_ip_map[k]
	# 	print (k, v)

	id_list = get_opt_dev(auth, host_addr)

	ref_out = 'mod_out.csv'
	with open(ref_out, 'w') as output:
		fieldnames = ['DevID', 'Family', "Module Name", "Description", "Location"]
		out_writer = csv.DictWriter(output, fieldnames=fieldnames)
		out_writer.writerow({'DevID': 'Dev ID', 'Family':'Family', "Module Name":"Module Name", "Description":"Description", "Location":"Location"})

		for id_num in id_list:
			inv_dets = get_dev_det(auth, host_addr, id_num)
			keys = sorted(inv_dets.keys())
			for k in inv_dets:
				v = inv_dets[k]
				# print (k,v)
				out_writer.writerow({'DevID': k, "Family":v[0], "Module Name":v[1], "Location":v[3], "Description":v[2]})


	