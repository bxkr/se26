package com.project.forecastfetcher.service;


import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.project.forecastfetcher.dto.*;
import com.project.forecastfetcher.model.DailyData;
import com.project.forecastfetcher.model.Measurement;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Valid;
import jakarta.validation.Validator;
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
import reactor.core.scheduler.Schedulers;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.HeadObjectRequest;
import software.amazon.awssdk.services.s3.model.NoSuchKeyException;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;


import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.stream.Collectors;


@Service
@Slf4j
public class EventProcessor {

    private final S3Client s3Client;
    private final KafkaTemplate<String, Object> kafkaTemplate;
    private WebClient webClient = WebClient.create();
    private final Validator validator;
    private final ObjectMapper objectMapper = new ObjectMapper().registerModule(new JavaTimeModule());

    public EventProcessor(
        S3Client s3Client,
        KafkaTemplate<String, Object> kafkaTemplate,
        Validator validator
    ) {
        this.s3Client = s3Client;
        this.kafkaTemplate = kafkaTemplate;
        this.validator = validator;
    }

    @Value("${app.external-api-url}")
    private String externalApiUrl;

    @Value("${app.coordinates-api-url}")
    private String coordinatesApi;

    @Value("${app.s3.bucket-name}")
    private String bucketName;

    @Value("${app.kafka.output-topic}")
    private String outputTopic;

    @KafkaListener(topics = "${app.kafka.input-topic}", groupId = "s3-uploader-forecast-group")
    public void handleEvent(@Valid @Payload InputEvent event, Acknowledgment ack) {

        log.info(">> Получено событие. Обработка данных для ID: {}", event.event_id());

        if(event.wmo_indexes().isEmpty()){
            log.info("Получен пустой список RequestedWmoIndexes.");
            ack.acknowledge();
            return;
        }
        if((event.date_from() == null) || (event.date_to() == null)){
            log.info("Получены невалидные даты.");
            ack.acknowledge();
            return;
        }
        LocalDate dt_date_from = LocalDate.parse(event.date_from());
        LocalDate dt_date_to = LocalDate.parse(event.date_to());

        if(dt_date_from.isAfter(dt_date_to)){
            log.info("Получены невалидные даты.");
            ack.acknowledge();
            return;
        }

        try {


            ConcurrentLinkedQueue<String> s3Keys = new ConcurrentLinkedQueue<>();

            Set<String> targetWmoIndexes = event.wmo_indexes().stream()
                    .map(String::valueOf)
                    .collect(Collectors.toSet());


                    Flux.fromIterable(targetWmoIndexes)
                    .flatMapSequential(index -> webClient.get()
                            .uri(coordinatesApi + "/wmo-indexes/{wmo_index}/coordinates", index)
                            .retrieve()
                            .bodyToMono(Coordinates.class)
                            .doOnNext(response -> {
                                Set<ConstraintViolation<Coordinates>> violations = validator.validate(response);
                                if (!violations.isEmpty()) {
                                    throw new IllegalArgumentException("Ошибка валидации координат: " + violations);
                                }
                            })
                    )
                    .flatMapSequential(coordinates -> webClient.get()
                            .uri(UriComponentsBuilder.fromUriString(externalApiUrl)
                                    .queryParam("latitude", coordinates.getLat())
                                    .queryParam("longitude", coordinates.getLng())
                                    .queryParam("start_date", dt_date_from)
                                    .queryParam("end_date", dt_date_to)
                                    .queryParam("daily", "temperature_2m_max,temperature_2m_min,precipitation_sum,temperature_2m_mean")
                                    .queryParam("timezone", "auto")
                                    .build()
                                    .toUri()
                            )
                            .retrieve()
                            .bodyToMono(ForecastResponse.class)
                            .map(forecast -> new CoordinateAndForecast(coordinates, forecast))
                    )

                    .collectList()

                    .map(this::convertToApiResponses)
                    .flatMapIterable(list -> list)
                    .flatMap(response -> Mono.fromRunnable(() -> {
                                String dailyS3Key = "forecast/date=" + response.getDate().toString() + ".json";

                                if (isObjectExists(bucketName, dailyS3Key)) {
                                    log.info("Файл для даты {} уже существует в S3. Пропускаем перезапись.", response.getDate());
                                    s3Keys.add(dailyS3Key);
                                    return;
                                }

                                try {
                                    String jsonPayload = objectMapper.writeValueAsString(response);
                                    s3Client.putObject(
                                            PutObjectRequest.builder()
                                                    .bucket(bucketName)
                                                    .key(dailyS3Key)
                                                    .contentType("application/json")
                                                    .build(),
                                            RequestBody.fromString(jsonPayload)
                                    );
                                    s3Keys.add(dailyS3Key);
                                    log.info("Файл успешно загружен в S3: {}", dailyS3Key);
                                } catch (Exception e) {
                                    log.error("Ошибка сохранения в S3 для даты {}: {}", response.getDate(), e.getMessage());
                                    throw new RuntimeException("Сбой записи в S3", e);
                                }
                            }).subscribeOn(Schedulers.boundedElastic())
                            , 5
                    )
                    .then()
                    .block(java.time.Duration.ofMinutes(3));







            if (s3Keys.isEmpty()) {
                log.warn("Ни один файл не был сохранен в S3 для ID: {}", event.event_id());
                ack.acknowledge();
                return;
            }

            OutputReceipt receipt = new OutputReceipt(
                    UUID.randomUUID().toString(), event.trace_id(),
                    "weather.actual.raw.created", "historical_fetcher", bucketName,
                    new ArrayList<>(s3Keys), event.date_from(),
                    event.date_to(), event.schema_version(), LocalDateTime.now().toString()
            );

            kafkaTemplate.send(outputTopic, event.event_id(), receipt).get(10, java.util.concurrent.TimeUnit.SECONDS);
            log.info("Успешно отправлена квитанция в Kafka для ID: {}", event.event_id());

            ack.acknowledge();
            log.info(">> Событие {} успешно обработано и подтверждено", event.event_id());

        } catch (Exception e) {
            log.error("Критический сбой при обработке события ID: {}.", event.event_id(), e);
            throw new RuntimeException("Ошибка обработки события Kafka", e);
        }

    }


    private boolean isObjectExists(String bucket, String key) {
        try {
            s3Client.headObject(HeadObjectRequest.builder().bucket(bucket).key(key).build());
            return true;
        } catch (NoSuchKeyException e) {
            return false;
        } catch (Exception e) {
            log.error("Не удалось проверить наличие объекта {} в S3 из-за сетевой ошибки", key, e);
            return false;
        }
    }

    private record CoordinateAndForecast(Coordinates coordinates, ForecastResponse forecast) {}
    private List<ApiResponse> convertToApiResponses(List<CoordinateAndForecast> pairs) {

        Map<LocalDate, List<Measurement>> measurementsByDate = new TreeMap<>();

        for (CoordinateAndForecast pair : pairs) {
            Coordinates coords = pair.coordinates();
            ForecastResponse forecast = pair.forecast();

            if (forecast == null || forecast.getDaily() == null || forecast.getDaily().getTime() == null) {
                continue;
            }

            DailyData daily = forecast.getDaily();
            List<LocalDate> dates = daily.getTime();


            for (int i = 0; i < dates.size(); i++) {
                LocalDate date = dates.get(i);


                Double maxTemp = (daily.getTemperature2mMax() != null && daily.getTemperature2mMax().size() > i) ? daily.getTemperature2mMax().get(i) : null;
                Double minTemp = (daily.getTemperature2mMin() != null && daily.getTemperature2mMin().size() > i) ? daily.getTemperature2mMin().get(i) : null;
                Double avgTemp = (daily.getTemperature2mMean() != null && daily.getTemperature2mMean().size() > i) ? daily.getTemperature2mMean().get(i) : null;
                Double precipitation = (daily.getPrecipitationSum() != null && daily.getPrecipitationSum().size() > i) ? daily.getPrecipitationSum().get(i) : null;


                Measurement measurement = new Measurement(
                        coords.getWmo_index(),
                        minTemp,
                        avgTemp,
                        maxTemp,
                        precipitation
                );


                measurementsByDate.computeIfAbsent(date, k -> new ArrayList<>()).add(measurement);
            }
        }


        return measurementsByDate.entrySet().stream()
                .map(entry -> {
                    ApiResponse response = new ApiResponse();
                    response.setDate(entry.getKey());
                    response.setStations(entry.getValue());
                    return response;
                })
                .toList();
    }

}


