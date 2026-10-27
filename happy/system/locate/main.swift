// Prints where this Mac is as one line of JSON; it runs inside an app bundle because macOS shows the location prompt only for one.
import CoreLocation
import Foundation

final class Ask: NSObject, CLLocationManagerDelegate {
    let manager = CLLocationManager()
    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyHundredMeters
    }
    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        switch manager.authorizationStatus {
        case .notDetermined: manager.requestWhenInUseAuthorization()
        case .denied, .restricted: say(["error": "denied"])
        default: manager.requestLocation()
        }
    }
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let place = locations.last else { return }
        say(["lat": place.coordinate.latitude, "lon": place.coordinate.longitude, "accuracy": place.horizontalAccuracy])
    }
    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        say(["error": error.localizedDescription])
    }
    func say(_ answer: [String: Any]) {
        let data = try! JSONSerialization.data(withJSONObject: answer)
        print(String(data: data, encoding: .utf8)!)
        exit(0)
    }
}

let ask = Ask()
DispatchQueue.main.asyncAfter(deadline: .now() + 15) { ask.say(["error": "timed out"]) }
RunLoop.main.run()
