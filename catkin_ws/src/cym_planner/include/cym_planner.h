#ifndef CYM_PLANNER_H_
#define CYM_PLANNER_H_

#include <nav_core/base_local_planner.h>
#include <opencv2/core/mat.hpp>
#include <ros/ros.h>
#include <sensor_msgs/Image.h>
#include <std_msgs/Bool.h>


namespace cym_planner
{


    class CymPlanner : public nav_core::BaseLocalPlanner
    {
      public:
        CymPlanner();
        ~CymPlanner();

        void initialize(std :: string name, tf2_ros :: Buffer* tf, costmap_2d :: Costmap2DROS* costmap_ros);
        bool setPlan(const std :: vector<geometry_msgs :: PoseStamped>& plan);
        bool computeVelocityCommands(geometry_msgs :: Twist& cmd_vel);
        bool isGoalReached();

      private:
        void carryModeCallback(const std_msgs::Bool::ConstPtr& message);
        void publishImage(const cv::Mat& image, const std::string& frame_id,
                          const ros::Publisher& publisher);
        ros::Subscriber carry_mode_sub_;
        ros::Publisher map_image_pub_;
        ros::Publisher plan_image_pub_;
        std::string map_image_topic_;
        std::string plan_image_topic_;
        bool carry_mode_;
        double carry_speed_scale_;
    };
} // namespace cym_planner

#endif // CYM_PLANNER_H_
