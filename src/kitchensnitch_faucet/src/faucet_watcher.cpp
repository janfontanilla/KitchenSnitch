// Detects a running tap through constant motion in a small region under the spout
// and publishes FaucetEvent STARTED / STOPPED (with duration).
#include <algorithm>
#include <memory>
#include <vector>

#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>

#include "cv_bridge/cv_bridge.hpp"
#include "kitchensnitch_interfaces/msg/faucet_event.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/image.hpp"

using kitchensnitch_interfaces::msg::FaucetEvent;

class FaucetWatcher : public rclcpp::Node
{
public:
  FaucetWatcher()
  : Node("faucet_watcher")
  {
    zone_ = declare_parameter<std::vector<double>>("faucet_zone", {0.25, 0.35, 0.08, 0.12});
    motion_threshold_ = declare_parameter<double>("faucet_motion_threshold", 0.15);
    pixel_diff_ = declare_parameter<int>("pixel_diff_threshold", 25);
    start_hold_s_ = declare_parameter<double>("start_hold_s", 1.0);
    stop_hold_s_ = declare_parameter<double>("stop_hold_s", 1.5);

    pub_ = create_publisher<FaucetEvent>("/events/faucet", 10);
    sub_ = create_subscription<sensor_msgs::msg::Image>(
      "/camera/image_raw", rclcpp::SensorDataQoS(),
      std::bind(&FaucetWatcher::onImage, this, std::placeholders::_1));
    RCLCPP_INFO(get_logger(), "faucet_watcher ready");
  }

private:
  void onImage(const sensor_msgs::msg::Image::ConstSharedPtr msg)
  {
    cv_bridge::CvImageConstPtr cv_ptr;
    try {
      cv_ptr = cv_bridge::toCvShare(msg, "mono8");
    } catch (const cv_bridge::Exception & e) {
      RCLCPP_ERROR_THROTTLE(get_logger(), *get_clock(), 5000, "cv_bridge: %s", e.what());
      return;
    }

    const cv::Rect roi = zoneToRect(cv_ptr->image.cols, cv_ptr->image.rows);
    cv::Mat crop;
    cv::GaussianBlur(cv_ptr->image(roi), crop, cv::Size(5, 5), 0);

    if (prev_.empty() || prev_.size() != crop.size()) {
      prev_ = crop.clone();
      return;
    }

    cv::Mat diff, mask;
    cv::absdiff(crop, prev_, diff);
    cv::threshold(diff, mask, pixel_diff_, 255, cv::THRESH_BINARY);
    prev_ = crop.clone();

    const double ratio = static_cast<double>(cv::countNonZero(mask)) / mask.total();
    const bool moving = ratio > motion_threshold_;

    // Use the image timestamp so replaying a bag gives the same durations as live.
    double t = rclcpp::Time(msg->header.stamp).seconds();
    if (t == 0.0) {
      t = now().seconds();
    }
    update(moving, t, msg->header.stamp);
  }

  void update(bool moving, double t, const builtin_interfaces::msg::Time & stamp)
  {
    if (!running_) {
      if (!moving) {
        run_since_ = -1.0;
        return;
      }
      if (run_since_ < 0.0) {
        run_since_ = t;
      }
      if (t - run_since_ >= start_hold_s_) {
        running_ = true;
        run_start_ = run_since_;
        last_motion_ = t;
        publish(FaucetEvent::STARTED, 0.0F, stamp);
      }
      return;
    }

    // Short dropouts (a hand or the pitcher crossing the stream) don't end the run.
    if (moving) {
      last_motion_ = t;
    } else if (t - last_motion_ >= stop_hold_s_) {
      running_ = false;
      run_since_ = -1.0;
      publish(FaucetEvent::STOPPED, static_cast<float>(last_motion_ - run_start_), stamp);
    }
  }

  void publish(uint8_t event, float duration, const builtin_interfaces::msg::Time & stamp)
  {
    FaucetEvent out;
    out.stamp = stamp;
    out.event = event;
    out.duration_s = duration;
    pub_->publish(out);
    RCLCPP_INFO(
      get_logger(), "faucet %s (%.1f s)", event == FaucetEvent::STARTED ? "STARTED" : "STOPPED",
      duration);
  }

  cv::Rect zoneToRect(int width, int height) const
  {
    if (zone_.size() != 4) {
      return cv::Rect(0, 0, width, height);
    }
    const int x0 = std::clamp(static_cast<int>(zone_[0] * width), 0, width - 1);
    const int y0 = std::clamp(static_cast<int>(zone_[1] * height), 0, height - 1);
    const int x1 = std::clamp(static_cast<int>((zone_[0] + zone_[2]) * width), x0 + 1, width);
    const int y1 = std::clamp(static_cast<int>((zone_[1] + zone_[3]) * height), y0 + 1, height);
    return cv::Rect(x0, y0, x1 - x0, y1 - y0);
  }

  std::vector<double> zone_;
  double motion_threshold_{0.15};
  int pixel_diff_{25};
  double start_hold_s_{1.0};
  double stop_hold_s_{1.5};

  cv::Mat prev_;
  bool running_{false};
  double run_since_{-1.0};
  double run_start_{0.0};
  double last_motion_{0.0};

  rclcpp::Publisher<FaucetEvent>::SharedPtr pub_;
  rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr sub_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<FaucetWatcher>());
  rclcpp::shutdown();
  return 0;
}
