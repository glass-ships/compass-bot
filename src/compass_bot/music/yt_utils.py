"""Modified from PyYouTube by @mrlokaman (MIT License)"""

import re
import urllib.request
import json


class SearchYT:
	"""Search for videos matching keywords"""
	def __init__(self, keywords:str, limit=15):
		url = "https://www.youtube.com/results?search_query=" + keywords.replace(" ", "+")
		html = urllib.request.urlopen(url)
		self.limit= limit
		self.source = html.read().decode('utf8')
		
	def videos(self):
		limit = self.limit
		source = self.source
		data  = re.findall('{\"videoRenderer\":{\"videoId\":\"(\S{11})\",\"thumbnail\":{\"thumbnails\":\[{\"url\":\"(\S+)\",\"width\":360,\"height\":202},{\"url\":\"(\S+)\",\"width\":720,\"height\":404}\]},\"title\":{\"runs\":\[{\"text\":\"(.+?)\"}\],\"accessibility\":{\"accessibilityData\":{\"label\":\"(.+?)\"}}},\"longBylineText\"',source)[:limit]
		data_ = []
		for i in data:
				js_data = {"id":"",
		            "title":"", 
		             "thumb" : "" ,
		              "simple_data":""}
				js_data['id'] = i[0]
				js_data['title'] = i[3]
				js_data['thumb'] = i[1],i[2]
				js_data['simple_data'] = i[4]
				data_.append(js_data)
		value =  json.dumps(data_ )
		return json.loads(value)
						
class Data:
	"""Get YouTube Video Data"""
	def __init__(self,link):
			headers = { 'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)' }
			res = urllib.request.Request(link, headers=headers)
			html = urllib.request.urlopen(res)
			self.source = html.read().decode('utf8')
	
	# # Get Video id 
	# def id(self):
	# 	try:
	# 		videodetails=re.findall("\"videoDetails\":\{(.+?),\"isOwnerViewing", self.source)[0]
	# 	except:
	# 		return None
    #     # Get id , title From videodetails variable
	# 	try:
	# 		id = re.findall("\"videoId\":\"(\S{11})",videodetails)[0]
	# 		return id 
	# 	except:
	# 		return None
	
	# # Get Video Title 	
	# def title(self):
	# 	try:
	# 		videodetails=re.findall("\"videoDetails\":\{(.+?),\"isOwnerViewing", self.source)[0]
	# 	except:
	# 		return None
	# 	try:
	# 		# Get id , title From videodetails variable
	# 		title = re.findall("\"title\":\"(.+?)\",",videodetails)[0]
	# 		return title 
	# 	except:
	# 		return None

	# # Get Thumbnails Link From Youtube Video 
	# def thumb(self):
	# 		try :
	# 			thumb= re.findall("\"thumbnails\":\[\{\"url\":\"(.+?)\",\"width",self.source )[0]
	# 			return thumb
	# 		except:
	# 			return None
			
	# # Get Video Publish Date 	
	# def publish_date(self):
	# 	try:
	# 		publish_date = re.findall("\"publishDate\":\"(\d{4}-\d{2}-\d{2})", self.source)[0]
	# 		return publish_date
	# 	except:
	# 		return None

	# # Get Views Of the Video
	# def views(self):
	# 	try:      		 
	# 		views = re.findall("\"viewCount\":\"(\d+)",self.source)[0]
	# 		return views
	# 	except:
	# 		return None
	
	# # Get Category Of The Video 
	# def category(self):
	# 	try:      		
	# 		category = re.findall("\"category\":\"(.+?)\",", self.source)[0]
	# 		return category
	# 	except:
	# 		return None

	# # Get Channel Name 
	# def channel_name(self):
	# 		try:
	# 			channelName = re.findall("\"channelName\":\"(.+?)\",", self.source)[0]
	# 			return channelName
	# 		except:
	# 			try:
	# 				channelName = re.findall("\"ownerChannelName\":\"(.+?)\",\"uploadDate",self.source)[0]
	# 				return channelName
	# 			except:
	# 				return None
	
	# # Get YouTube Videos tag 		
	# def tags(self):
	# 	try:
	# 		tags = re.findall("\<meta name=\"keywords\" content=\"(.+?)\">",self.source)[0]
	# 		return tags
	# 	except:
	# 		return None
			
    # Construct a dictionary of the data
	def data(self):

		videodetails = re.findall("\"videoDetails\":\{(.+?),\"isOwnerViewing", self.source)[0] or None
		id = re.findall("\"videoId\":\"(\S{11})",videodetails)[0] or None
		title = re.findall("\"title\":\"(.+?)\",",videodetails)[0] or None
		duration = re.findall("\"lengthSeconds\":\"(\d+)", self.source)[0] or None
		try:
			thumbnail = re.findall("\"thumbnails\":\[\{\"url\":\"(.+?)\",\"width",self.source )[0]
			thumbnail = thumbnail.replace("hqdefault.jpg","maxresdefault.webp")
			thumbnail = thumbnail.replace("/vi/","/vi_webp/")
			thumbnail = thumbnail.split("?")[0]
		except:
			thumbnail = None
		try:
			channelName = re.findall("\"channelName\":\"(.+?)\",", self.source)[0] or None
		except:
			try:
				channelName = re.findall("\"ownerChannelName\":\"(.+?)\",\"uploadDate",self.source)[0] or None
			except:
				channelName = None
		category = re.findall("\"category\":\"(.+?)\",", self.source)[0] or None
		publish_date = re.findall("\"publishDate\":\"(\d{4}-\d{2}-\d{2})", self.source)[0] or None
		tags = re.findall("\<meta name=\"keywords\" content=\"(.+?)\">",self.source)[0] or None
		views = re.findall("\"viewCount\":\"(\d+)",self.source)[0] or None
		
		DATA = { 
					"id": id,
					"url": f"https://www.youtube.com/watch?v={id}",
					"title": title,
					"duration": int(duration),
					"thumbnails": thumbnail,
					"views": views,
					"publishdate": publish_date,
					"category": category,
					"channel_name": channelName,
					"keywords":tags      	             
				}
		
		return DATA
