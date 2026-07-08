package com.project.weatherdatafetcher.filter;


import com.project.weatherdatafetcher.dto.InputEvent;

import org.apache.commons.logging.LogFactory;
import org.jspecify.annotations.NullMarked;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.listener.adapter.RecordFilterStrategy;
import org.springframework.kafka.support.KafkaUtils;
import org.springframework.kafka.support.serializer.SerializationUtils;
import org.springframework.core.log.LogAccessor;

@Configuration
@NullMarked
public class KafkaFilterConfig {

    private static final LogAccessor logger = new LogAccessor(LogFactory.getLog(KafkaFilterConfig.class));

    @Bean
    public RecordFilterStrategy<Object, Object> datasetTypeFilter() {
        return consumerRecord -> {

            System.out.println("Event is being filtered");
            if (SerializationUtils.getExceptionFromHeader(
                    consumerRecord,
                    KafkaUtils.VALUE_DESERIALIZER_EXCEPTION_HEADER,
                    logger) != null) {

                return false;
            }

            Object value = consumerRecord.value();


            if (value instanceof InputEvent event) {
                if (event.dataset_type() == null) {
                    return true;
                }

                return !event.dataset_type().equals("weather-raw");
            }

            return false;
        };
    }
}