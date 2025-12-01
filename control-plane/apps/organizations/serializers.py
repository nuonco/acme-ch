from rest_framework import serializers
from .models import Organization, OrganizationMember


class OrganizationMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = OrganizationMember
        fields = ['id', 'user_email', 'role', 'created_on']
        read_only_fields = ['id', 'created_on']


class OrganizationSerializer(serializers.ModelSerializer):
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)
    members_list = OrganizationMemberSerializer(
        source='organizationmember_set',
        many=True,
        read_only=True
    )

    class Meta:
        model = Organization
        fields = [
            'id',
            'name',
            'slug',
            'region',
            'deploy_headlamp',
            'nuon_install_id',
            'created_by',
            'created_by_email',
            'members_list',
            'created_on',
            'updated_on',
        ]
        read_only_fields = [
            'id',
            'slug',
            'nuon_install_id',
            'created_by',
            'created_by_email',
            'created_on',
            'updated_on',
        ]


