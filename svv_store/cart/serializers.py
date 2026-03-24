class CartItemSerializer(serializers.ModelSerializer):
    cart_item_id = serializers.IntegerField(source='id', read_only=True)
    product_id = serializers.IntegerField(source='product_variant.product.id', read_only=True)
    product_name = serializers.CharField(source='product_variant.product.name', read_only=True)
    product_variant_id = serializers.IntegerField(source='product_variant.id', read_only=True)
    product_variant = serializers.StringRelatedField()
    product_image = serializers.SerializerMethodField()
    price = serializers.DecimalField(
        source='product_variant.price',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    discounted_price = serializers.DecimalField(
        source='product_variant.discounted_price',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = CartItem
        fields = [
            'cart_item_id',
            'product_id',
            'product_name',
            'product_variant_id',
            'product_variant',
            'product_image',
            'price',
            'discounted_price',
            'quantity',
        ]

    def get_product_image(self, obj):
        image = obj.product_variant.product.images.first()
        return image.image if image else None
