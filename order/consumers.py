from channels.generic.websocket import AsyncJsonWebsocketConsumer

class OrderNotificationConsumer(AsyncJsonWebsocketConsumer): # Consumer to send order notifications to users(WebSocket endpoint)
    async def connect(self):# On WebSocket connection
        user = self.scope["user"] # Get the authenticated user from scope

        if user.is_anonymous:
            await self.close()
            return
        # every websocket connection is added to a group based on user id
        self.group_name = f"user_{user.id}" # Define group name based on user ID
        await self.channel_layer.group_add(self.group_name, self.channel_name) 
        await self.accept()

    async def send_notification(self, event):# Handler to send notification to WebSocket
        await self.send_json(event["data"])# Send JSON data to WebSocket client
