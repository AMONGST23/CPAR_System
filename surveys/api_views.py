from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import MaternalRecord
from .serializers import MaternalRecordSerializer


class SyncReceiveView(APIView):
    """
    POST /api/sync/
    Accepts a JSON body: {"records": [...]}
    Used by local servers to push data to the online server.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        records_data = request.data.get('records', [])
        if not isinstance(records_data, list):
            return Response({'error': 'Expected a list of records.'}, status=status.HTTP_400_BAD_REQUEST)

        saved, errors = [], []
        for record_data in records_data:
            # Remove read-only fields that shouldn't be set
            record_data.pop('id', None)
            serializer = MaternalRecordSerializer(data=record_data)
            if serializer.is_valid():
                serializer.save()
                saved.append(str(record_data.get('sync_uuid', '')))
            else:
                errors.append({'sync_uuid': record_data.get('sync_uuid'), 'errors': serializer.errors})

        return Response({
            'saved': len(saved),
            'errors': errors,
            'sync_uuids': saved,
        }, status=status.HTTP_200_OK)


class RecordListAPIView(APIView):
    """GET /api/records/ — list all records (for remote access)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        records = MaternalRecord.objects.all()
        serializer = MaternalRecordSerializer(records, many=True)
        return Response(serializer.data)
