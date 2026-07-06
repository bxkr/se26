package com.project.weatherdatafetcher.dto;
import jakarta.persistence.*;

import com.project.weatherdatafetcher.enums.RequestStatus;

public record OutputReceipt(
        String eventId,
        String s3Key,

        @Enumerated(EnumType.STRING)
        RequestStatus status
) {}
