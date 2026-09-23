package gt.edu.umg.fivercable.pagos.controller;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {
    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("service", "pagos-service", "status", "UP", "responsibility", "cobros pagos y comprobantes");
    }
}

