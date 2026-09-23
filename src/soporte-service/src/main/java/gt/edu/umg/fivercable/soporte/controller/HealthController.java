package gt.edu.umg.fivercable.soporte.controller;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {
    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("service", "soporte-service", "status", "UP", "responsibility", "tickets y soporte tecnico");
    }
}

