package com.project.weatherdatafetcher.filter;


import com.project.weatherdatafetcher.dto.InputEvent;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.jspecify.annotations.NonNull;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.listener.adapter.RecordFilterStrategy;

@Configuration
public class KafkaFilterConfig {

    @Bean
    public RecordFilterStrategy<String, InputEvent> datasetTypeFilter() {
        return new RecordFilterStrategy<String, InputEvent>() {
            @Override
            public boolean filter(@NonNull ConsumerRecord<String, InputEvent> consumerRecord) {
                InputEvent event = consumerRecord.value();

                if (event == null || event.datasetType() == null) {
                    return true;
                }

                return !event.datasetType().equals("weather-raw");
            }
        };
    }
}