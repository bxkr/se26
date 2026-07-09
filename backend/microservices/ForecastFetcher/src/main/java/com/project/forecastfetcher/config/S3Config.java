package com.project.forecastfetcher.config;


import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.core.client.config.ClientOverrideConfiguration;
import software.amazon.awssdk.core.retry.RetryPolicy;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.S3Configuration;

import java.net.URI;
import java.time.Duration;

@Configuration
public class S3Config {

    @Bean
    public S3Client s3Client(
            @Value("${app.s3.endpoint}") String endpoint,
            @Value("${app.s3.access-key}") String accessKey,
            @Value("${app.s3.secret-key}") String secretKey) {

        return S3Client.builder()
                .endpointOverride(URI.create(endpoint))
                .region(Region.of("ru-central-1"))
                .credentialsProvider(StaticCredentialsProvider.create(
                        AwsBasicCredentials.create(accessKey, secretKey)
                ))
                .serviceConfiguration(S3Configuration.builder()
                        .pathStyleAccessEnabled(true)
                        .build())
                // Default SDK retry policy has no bounded per-attempt/total
                // timeout, so a slow/retried call against Yandex Object
                // Storage can silently stall tens of seconds with nothing
                // above DEBUG level in the logs (observed: one GetObject in
                // mergeAndWrite took ~30s with zero ERROR/WARN output).
                // Bound both, and cap retries explicitly, so a repeat either
                // fails fast and loud or is visibly a real slow call, not a
                // silent stall.
                .overrideConfiguration(ClientOverrideConfiguration.builder()
                        .apiCallAttemptTimeout(Duration.ofSeconds(5))
                        .apiCallTimeout(Duration.ofSeconds(15))
                        .retryPolicy(RetryPolicy.builder().numRetries(2).build())
                        .build())
                .build();
    }
}