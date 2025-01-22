from django.db import migrations

def add_default_routes(apps, schema_editor):
    # Get the model
    UpstreamServer = apps.get_model('home', 'UpstreamServer')
    
    # Define the default routes
    default_routes = [
        {
            'route': 'basic',
            'display_name': 'Basic Histogram Server',
            'description': 'Server for basic histogram visualization'
        },
        {
            'route': 'general',
            'display_name': 'General Histogram Server',
            'description': 'Server for general histogram visualization'
        },
        {
            'route': 'ood',
            'display_name': 'OOD Analyzer Server',
            'description': 'Server for OOD analysis visualization'
        }
    ]
    
    # Add each default route
    for route_data in default_routes:
        UpstreamServer.objects.get_or_create(
            route=route_data['route'],
            defaults={
                'display_name': route_data['display_name'],
                'description': route_data['description']
            }
        )

def remove_default_routes(apps, schema_editor):
    # Get the model
    UpstreamServer = apps.get_model('home', 'UpstreamServer')
    # Remove the default routes
    UpstreamServer.objects.filter(route__in=['basic', 'general', 'ood']).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('home', '0001_initial'),  # Make sure this matches your previous migration
    ]

    operations = [
        migrations.RunPython(add_default_routes, remove_default_routes),
    ] 