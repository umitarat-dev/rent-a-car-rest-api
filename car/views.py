from drf_yasg.utils import swagger_auto_schema # Üst kısma ekle
from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from .models import Car, Reservation
from .serializers import CarSerializer, CarStaffSerializer, ReservationSerializer
from .permissions import IsStaffOrReadOnly
from rest_framework.permissions import IsAuthenticated

from django.db.models import Q, F

from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from django.utils import timezone

# for dinamic is_available field 
from django.db.models import Exists, OuterRef


class CarView(ModelViewSet):
    queryset = Car.objects.all()
    # Varsayılanı Staff yap ki Swagger tüm alanları (plate_number vb.) göstersin. Normal userlar için get_serializer_class methodu ile CarSerializer döneceğiz.
    serializer_class = CarStaffSerializer
    permission_classes = (IsStaffOrReadOnly,)  # [IsStaffOrReadOnly]
    
    # Swagger'a POST ve PUT işlemlerinde her zaman StaffSerializer kullanmasını söylüyoruz
    @swagger_auto_schema(request_body=CarStaffSerializer)
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(request_body=CarStaffSerializer)
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    # Serializer seçim mantığı
    def get_serializer_class(self):
        if self.request.user.is_staff:
            return CarStaffSerializer
        return CarSerializer
    
    def get_queryset(self):
        # 1. Temel Filtreleme: Staff her şeyi görür, normal user sadece aktif/müsait olanları
        if self.request.user.is_staff:
            queryset = Car.objects.all()
        else:
            queryset = Car.objects.filter(availability=True)

        start = self.request.query_params.get('start')
        # print(start)
        end = self.request.query_params.get('end')
        # print(end)
        
        # 2. Dinamik Müsaitlik Kontrolü: SADECE her iki tarih de varsa hesapla.
        if start and end:
            queryset = queryset.annotate(
                is_available=~Exists(
                    Reservation.objects.filter(
                        Q(car=OuterRef('pk')) &
                        Q(start_date__lt=end) &
                        Q(end_date__gt=start)
                    )
                )
            )
        else:
            # 3. KORUMA: Eğer tarih yoksa, 'is_available' alanını statik 'availability'den kopyala.
            # Bu sayede serializer hata vermez (AttributeError önlenir).
            queryset = queryset.annotate(is_available=F('availability'))
            
        return queryset

class ReservationView(ListCreateAPIView):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    permission_classes = (IsAuthenticated,)
    
    '''
    def create(self, request, *args, **kwargs):
        contidion: Eğer user'ın reservation yapmak istediği tarih ile kesişen bir reservasyonu var ise, measaj dön ve yeni bir reservation create etmesine mani ol! 
    '''
    def get_queryset(self):
        if self.request.user.is_staff:
            return super().get_queryset()
        return super().get_queryset().filter(customer=self.request.user)
    

class ReservationDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    # lookup_field = 'id'
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        # validse datayı dön, değilse hataları/errorları raise et.
        serializer.is_valid(raise_exception=True)
        
        end = serializer.validated_data.get('end_date')
        car = serializer.validated_data.get('car')
        start = instance.start_date # update edilecek instanceın start_date i
        today = timezone.now().date()

        if Reservation.objects.filter(car=car).exists(): # Bu car a ait reservation var mı?
            # a = Reservation.objects.filter(car=car, end_date__gte=today)
            # print(len(a))    
            
            for reserv in Reservation.objects.filter(car=car, end_date__gte=today):
                if start < reserv.start_date < end:
                    return Response({'message': 'Car is not available...'}) # eğer if bloğuna girerse burasını return et. (update yapma mesajı döndür!)

        return super().update(request, *args, **kwargs) # eğer if bloğuna girmezse burasını return et. (Normal olarak update yap!)



    
