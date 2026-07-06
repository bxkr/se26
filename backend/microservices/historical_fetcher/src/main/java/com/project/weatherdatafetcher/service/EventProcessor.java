package com.project.weatherdatafetcher.service;


import com.project.weatherdatafetcher.dto.ApiResponse;
import com.project.weatherdatafetcher.dto.InputEvent;

import com.project.weatherdatafetcher.dto.OutputReceipt;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Valid;
import jakarta.validation.Validator;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.util.UriComponentsBuilder;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;

import tools.jackson.databind.ObjectMapper;

import java.time.LocalDate;
import java.util.List;
import java.util.Set;

import static com.project.weatherdatafetcher.enums.RequestStatus.SUCCESS;


@Service
@Slf4j
@RequiredArgsConstructor
public class EventProcessor {

    private final S3Client s3Client;
    private final KafkaTemplate<String, Object> kafkaTemplate;
    private WebClient webClient = WebClient.create();
    private final Validator validator;
    private final ObjectMapper objectMapper;

    @Value("${app.external-api-url}")
    private String externalApiUrl;

    @Value("${app.s3.bucket-name}")
    private String bucketName;

    @Value("${app.kafka.output-topic}")
    private String outputTopic;

    @KafkaListener(topics = "${app.kafka.input-topic}", groupId = "s3-uploader-historical-group")
    public void handleEvent(@Valid @Payload InputEvent event, Acknowledgment ack) {
        log.info(">> Получено событие. Обработка данных для ID: {}", event.eventId());

        String s3Key = "raw_responses/date=" + event.startDate() + "/data_" + event.eventId() + ".json";

        try {
            List<LocalDate> dates = event.startDate()
                    .datesUntil(event.endDate().plusDays(1))
                    .toList();

            List<ApiResponse> validResponses = Flux.fromIterable(dates)
                    .flatMapSequential(date -> webClient.get()
                                    .uri(UriComponentsBuilder.fromUriString(externalApiUrl)
                                            .queryParam("date", date)
                                            .build()
                                            .toUri())
                                    .retrieve()
                                    .bodyToMono(ApiResponse.class)
                                    .map(response -> {
                                        Set<ConstraintViolation<ApiResponse>> violations = validator.validate(response);
                                        if (!violations.isEmpty()) {
                                            throw new IllegalArgumentException("Ошибка валидации ответа API: " + violations);
                                        }
                                        return response;
                                    })
                                    .onErrorResume(ex -> {
                                        log.error("Ошибка при обработке даты {}: {}", date, ex.getMessage());
                                        return Mono.empty();
                                    })
                            , 5)
                    .collectList()
                    .block();


            if (validResponses == null || validResponses.isEmpty()) {
                throw new RuntimeException("Не удалось получить валидные данные ни за один день");
            }

            String jsonPayload = objectMapper.writeValueAsString(validResponses);


            s3Client.putObject(
                    PutObjectRequest.builder()
                            .bucket(bucketName)
                            .key(s3Key)
                            .contentType("application/json")
                            .build(),
                    RequestBody.fromString(jsonPayload)
            );
            log.info("Сырой JSON успешно сохранен в S3 по ключу: {}", s3Key);


            OutputReceipt receipt = new OutputReceipt(event.eventId(), s3Key, SUCCESS);
            kafkaTemplate.send(outputTopic, event.eventId(), receipt).get();

            ack.acknowledge();
            log.info(">> Событие {} успешно обработано и подтверждено", event.eventId());

        } catch (Exception e) {

            log.error("Критический сбой при обработке события ID: {}.", event.eventId(), e);
            throw new RuntimeException("Ошибка обработки события Kafka", e);
        }
    }
}
