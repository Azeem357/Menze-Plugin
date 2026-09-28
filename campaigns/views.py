from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import AdCampaign
from .serializers import AdCampaignSerializer


class CampaignListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/campaigns/     → list all campaigns
    POST /api/campaigns/     → create new campaign
    One view handles both
    """
    queryset = AdCampaign.objects.all()
    serializer_class = AdCampaignSerializer
    
    def get_queryset(self):
        queryset = AdCampaign.objects.all()
        
        # Filter by platform
        platform = self.request.query_params.get(
            'platform'
        )
        if platform:
            queryset = queryset.filter(
                platform=platform
            )
        
        # Filter active only
        active = self.request.query_params.get('active')
        if active == 'true':
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('-created_at')


class CampaignDetailView(
    generics.RetrieveUpdateDestroyAPIView
):
    """
    GET    /api/campaigns/<id>/ → get one campaign
    PUT    /api/campaigns/<id>/ → update campaign
    DELETE /api/campaigns/<id>/ → delete campaign
    One view handles all three
    """
    queryset = AdCampaign.objects.all()
    serializer_class = AdCampaignSerializer


class CampaignUpdateSpendView(APIView):
    """
    POST /api/campaigns/<id>/update-spend/
    Updates campaign spend from ad platform.
    Custom logic → APIView needed
    """
    def post(self, request, pk):
        try:
            campaign = AdCampaign.objects.get(pk=pk)
        except AdCampaign.DoesNotExist:
            return Response(
                {'error': 'Campaign not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        campaign.spend = request.data.get(
            'spend', campaign.spend
        )
        campaign.impressions = request.data.get(
            'impressions', campaign.impressions
        )
        campaign.clicks = request.data.get(
            'clicks', campaign.clicks
        )
        campaign.save()
        
        return Response({
            'success': True,
            'campaign': AdCampaignSerializer(
                campaign
            ).data
        })
