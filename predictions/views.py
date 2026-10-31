from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import numpy as np

# Sales prediction endpoint
class SalesPredictionView(APIView):
    def get(self, request):
        try:
            from ai_models.predict_sales import predict_next_30_days

            # Get last 30 days sales from your DB
            # For now using dummy data
            recent_sales = list(np.random.randint(5000, 50000, 30))

            predictions = predict_next_30_days(recent_sales)

            return Response({
                'predictions': predictions,
                'days': list(range(1, 31)),
                'label': 'Next 30 Days Sales Forecast'
            })
        except Exception as e:
            return Response({'error': str(e)}, status=500)


# Product recommendation endpoint
class RecommendationView(APIView):
    def post(self, request):
        try:
            import pickle

            data = request.data
            category        = data.get('viewed_category', 'shirts')
            session_duration = int(data.get('session_duration', 120))
            pages_visited   = int(data.get('pages_visited', 3))
            added_to_cart   = int(data.get('added_to_cart', 0))

            with open('ai_models/saved_models/recommendation_model.pkl', 'rb') as f:
                clf = pickle.load(f)
            with open('ai_models/saved_models/label_encoders.pkl', 'rb') as f:
                encoders = pickle.load(f)

            le_cat  = encoders['category']
            le_item = encoders['item']

            cat_enc = le_cat.transform([category])[0]
            X = [[cat_enc, session_duration, pages_visited, added_to_cart]]

            pred_enc = clf.predict(X)[0]
            recommended = le_item.inverse_transform([pred_enc])[0]

            return Response({'recommended_item': recommended})

        except Exception as e:
            return Response({'error': str(e)}, status=500)
