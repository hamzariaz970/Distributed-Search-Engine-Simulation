package org.grobid.service.modules;

import com.codahale.metrics.MetricRegistry;
import com.fasterxml.jackson.databind.ObjectMapper;

import com.google.inject.AbstractModule;
import com.google.inject.Provides;

import jakarta.ws.rs.client.Client;
import jakarta.ws.rs.client.ClientBuilder;

import org.grobid.service.GrobidRestService;
import org.grobid.service.GrobidServiceConfiguration;
import org.grobid.service.exceptions.mapper.GrobidExceptionMapper;
import org.grobid.service.exceptions.mapper.GrobidExceptionsTranslationUtility;
import org.grobid.service.exceptions.mapper.GrobidServiceExceptionMapper;
import org.grobid.service.exceptions.mapper.WebApplicationExceptionMapper;
import org.grobid.service.process.GrobidRestProcessFiles;
import org.grobid.service.process.GrobidRestProcessGeneric;
import org.grobid.service.process.GrobidRestProcessString;
import org.grobid.service.process.GrobidRestProcessTraining;
import org.grobid.service.resources.HealthResource;

import ru.vyarus.dropwizard.guice.module.support.DropwizardAwareModule;

public class GrobidServiceModule extends DropwizardAwareModule<GrobidServiceConfiguration> {

    @Override
    public void configure() {
        bind(HealthResource.class);

        //REST
        bind(GrobidRestService.class);
        bind(GrobidRestProcessFiles.class);
        bind(GrobidRestProcessGeneric.class);
        bind(GrobidRestProcessString.class);
        bind(GrobidRestProcessTraining.class);

        //Exception Mappers
        bind(GrobidServiceExceptionMapper.class);
        bind(GrobidExceptionsTranslationUtility.class);
        bind(GrobidExceptionMapper.class);
        bind(WebApplicationExceptionMapper.class);
    }

    @Provides
    protected ObjectMapper getObjectMapper() {
        return environment().getObjectMapper();
    }

    @Provides
    protected MetricRegistry provideMetricRegistry() {
        return getMetricRegistry();
    }

    //for unit tests
    protected MetricRegistry getMetricRegistry() {
        return environment().metrics();
    }

    @Provides
    Client provideClient() {
        return ClientBuilder.newClient();
    }

}
