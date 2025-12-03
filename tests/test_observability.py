import nexor.observability as observability


def test_parse_otlp_headers_discards_invalid_pairs():
    raw_headers = 'alpha=1, invalid, beta = 2, gamma=three=four'
    parsed = observability.parse_otlp_headers(raw_headers)
    assert parsed == {
        'alpha': '1',
        'beta': '2',
        'gamma': 'three=four',
    }


def test_build_resource_respects_environment_and_extra(monkeypatch):
    monkeypatch.setenv('SERVICE_NAMESPACE', 'team-namespace')
    monkeypatch.setenv('DEPLOYMENT_ENV', 'staging')
    monkeypatch.setenv('SERVICE_INSTANCE_ID', 'instance-123')

    resource = observability.build_resource(
        service_name='payment',
        extra={'team': 'payments'},
    )

    attrs = resource.attributes
    assert attrs['service.name'] == 'payment'
    assert attrs['service.namespace'] == 'team-namespace'
    assert attrs['deployment.environment'] == 'staging'
    assert attrs['service.instance.id'] == 'instance-123'
    assert attrs['team'] == 'payments'


def test_init_observability_initialises_providers(monkeypatch):
    calls = []

    def fake_provider(resource):
        calls.append(('provider', resource))

    def fake_metrics(resource):
        calls.append(('metrics', resource))

    monkeypatch.setattr(observability, '_ensure_provider', fake_provider)
    monkeypatch.setattr(observability, '_ensure_metrics_provider', fake_metrics)

    observability.init_observability(
        service_name='connector',
        service_namespace='t1',
        deployment_environment='prod',
        extra={'region': 'eu-central'},
    )

    assert calls[0][0] == 'provider'
    assert calls[1][0] == 'metrics'
    assert calls[0][1] is calls[1][1]
    attrs = calls[0][1].attributes
    assert attrs['service.name'] == 'connector'
    assert attrs['region'] == 'eu-central'


def test_init_otel_fastapi_instruments_app(monkeypatch):
    init_calls = []

    def fake_init_observability(*, service_name, service_namespace=None, deployment_environment=None, extra=None):
        init_calls.append(
            {
                'service_name': service_name,
                'service_namespace': service_namespace,
                'deployment_environment': deployment_environment,
                'extra': extra,
            }
        )

    class DummyInstrumentor:
        calls = []

        @classmethod
        def uninstrument_app(cls, app):
            cls.calls.append(('un', app))

        @classmethod
        def instrument_app(cls, app):
            cls.calls.append(('in', app))

    monkeypatch.setattr(observability, 'init_observability', fake_init_observability)
    monkeypatch.setattr(observability, 'FastAPIInstrumentor', DummyInstrumentor)

    dummy_app = object()
    observability.init_otel_fastapi(dummy_app, service_name='gateway')

    assert init_calls == [
        {
            'service_name': 'gateway',
            'service_namespace': None,
            'deployment_environment': None,
            'extra': None,
        },
    ]
    assert DummyInstrumentor.calls == [('un', dummy_app), ('in', dummy_app)]
